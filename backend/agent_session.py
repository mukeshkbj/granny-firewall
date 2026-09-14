"""Voice Agent API WebSocket client.

One session = one call. Protocol (per AssemblyAI docs/tutorial):
  - wss://agents.assemblyai.com/v1/ws, Authorization: Bearer <key>
  - first message session.update {system_prompt, greeting, tools, output:{voice}}
  - wait for session.ready, then stream input.audio (base64 PCM16 24kHz, ~50ms)
  - events: reply.audio | tool.call | reply.done | transcript.user |
            transcript.agent | session.ready
  - tool results are sent inside the reply.done handler, not on tool.call
  - reply.done status=interrupted → drop pending tool results + flush playback
"""

import asyncio
import base64
import json
import os

import websockets

from tools import TOOLS, dispatch_tool

VOICE_AGENT_WS = "wss://agents.assemblyai.com/v1/ws"
SAMPLE_RATE = 24000


class CallContext:
    """Shared per-call state handed to the tool dispatcher."""

    def __init__(self, detector, log, codeword=None):
        self.detector = detector
        self.log = log
        self.codeword = codeword or os.environ.get("FAMILY_CODEWORD", "blueberry")
        self.persona = "screener"
        self.passed = False
        self.should_end = False
        self.session_id = None


class AgentSession:
    def __init__(self, ctx: CallContext, system_prompt: str, voice: str,
                 greeting: str, on_event, on_audio=None, tools=None,
                 input_encoding: str = "audio/pcm",
                 output_encoding: str = "audio/pcm"):
        """on_event(dict) and on_audio(bytes) are async callbacks.
        Use input/output_encoding="audio/pcmu" for telephony (8kHz μ-law)."""
        self.ctx = ctx
        self.system_prompt = system_prompt
        self.voice = voice
        self.greeting = greeting
        self.on_event = on_event
        self.on_audio = on_audio
        self.input_encoding = input_encoding
        self.output_encoding = output_encoding
        self.tools = TOOLS if tools is None else tools
        self._audio_in: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._ws = None
        self._tasks: list[asyncio.Task] = []
        self.ready = asyncio.Event()
        self.done = asyncio.Event()

    async def start(self):
        key = os.environ["ASSEMBLYAI_API_KEY"]
        self._ws = await websockets.connect(
            VOICE_AGENT_WS, additional_headers={"Authorization": f"Bearer {key}"}
        )
        session_cfg = {
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "output": {"voice": self.voice},
            "input": {"format": {"encoding": self.input_encoding}},
        }
        session_cfg["output"]["format"] = {"encoding": self.output_encoding}
        if self.greeting:
            session_cfg["greeting"] = self.greeting  # omit → agent listens first
        await self._ws.send(json.dumps({
            "type": "session.update",
            "session": session_cfg,
        }))
        self._tasks = [
            asyncio.create_task(self._send_loop()),
            asyncio.create_task(self._recv_loop()),
        ]

    async def send_audio(self, pcm: bytes):
        await self._audio_in.put(pcm)

    async def close(self):
        await self._audio_in.put(None)
        for t in self._tasks:
            t.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001,S110 - best-effort close
                pass
        self.done.set()

    # -- internals ----------------------------------------------------------

    async def _send_loop(self):
        await self.ready.wait()
        while True:
            chunk = await self._audio_in.get()
            if chunk is None or self.done.is_set():
                return
            await self._ws.send(json.dumps({
                "type": "input.audio",
                "audio": base64.b64encode(chunk).decode(),
            }))

    async def _recv_loop(self):
        pending_tools: list[dict] = []
        try:
            async for raw in self._ws:
                event = json.loads(raw)
                kind = event.get("type")

                if kind == "session.ready":
                    self.ctx.session_id = event.get("session_id")
                    self.ready.set()
                    await self.on_event({"type": "session_ready",
                                         "session_id": self.ctx.session_id})

                elif kind == "reply.audio":
                    audio = base64.b64decode(event["data"])
                    if self.on_audio:
                        await self.on_audio(audio)

                elif kind == "tool.call":
                    result = dispatch_tool(
                        event["name"], event.get("arguments", {}), self.ctx)
                    pending_tools.append(
                        {"call_id": event["call_id"], "result": result})
                    await self.on_event({
                        "type": "tool_call", "name": event["name"],
                        "arguments": event.get("arguments", {}),
                        "result": result})

                elif kind == "reply.done":
                    if event.get("status") == "interrupted":
                        pending_tools.clear()
                        await self.on_event({"type": "interrupted"})
                    else:
                        for t in pending_tools:
                            value = t["result"]
                            if not isinstance(value, str):
                                value = json.dumps(value)
                            await self._ws.send(json.dumps({
                                "type": "tool.result",
                                "call_id": t["call_id"],
                                "result": value,
                            }))
                        pending_tools.clear()

                elif kind == "transcript.user":
                    await self._on_caller_text(event.get("text", ""))

                elif kind == "transcript.agent":
                    text = event.get("text", "")
                    self.ctx.log.add_transcript("agent", text)
                    await self.on_event({"type": "transcript",
                                         "speaker": "agent", "text": text})

                elif kind == "session.ended" or kind == "error":
                    await self.on_event({"type": kind, "detail": event})
                    self.done.set()
                    return
        except websockets.ConnectionClosed:
            pass
        finally:
            self.done.set()
            await self.on_event({"type": "session_closed"})

    async def _on_caller_text(self, text: str):
        self.ctx.log.add_transcript("caller", text)
        markers = self.ctx.detector.feed(text, speaker="caller")
        await self.on_event({"type": "transcript", "speaker": "caller",
                             "text": text})
        for m in markers:
            self.ctx.log.log("marker", **m.to_dict())
            await self.on_event({"type": "marker", **m.to_dict()})
        if markers:
            await self.on_event({"type": "risk", **self.ctx.detector.snapshot()})
