"""Analyze mode: stream a call recording through Universal-Streaming and run
the detector on every turn.

Uses the official assemblyai SDK (thread-based callbacks) inside an asyncio
wrapper: SDK callbacks push TurnEvents into a queue drained by the async loop;
the audio feed runs in a worker thread paced at real time.
"""

import asyncio
import os
import queue
import threading
import time

from assemblyai.streaming.v3 import (
    Encoding,
    RealTimeEvents,
    RealTimeParameters,
    RealTimeTranscriber,
    RealTimeTranscriberOptions,
)
from assemblyai.streaming.v3.models import LLMGatewayConfig

from audio import chunk_bytes, load_pcm16

ANALYZE_RATE = 16000

# Third detection source: LLM Gateway runs this prompt against every
# finalized turn inside the streaming session — still 100% AssemblyAI.
LLM_TURN_PROMPT = (
    "You are a fraud-detection classifier on a screened phone call. "
    "Classify the caller's latest turn for scam signals. Reply with ONLY "
    "compact JSON: {\"category\": one of impersonation|urgency_threat|"
    "payment_vector|credential_phishing|isolation|too_good_to_be_true|"
    "grandparent_emergency|none, \"severity\": 1-3, \"quote\": \"the shortest "
    "verbatim phrase that triggered it\"}. Turn: {{turn}}"
)


def _parse_llm_marker(data: dict):
    """LLMGatewayResponse event.data -> (category, severity, quote) or None."""
    import json as _json
    try:
        content = data["choices"][0]["message"]["content"]
        if content.strip().startswith("```"):
            content = content.strip().split("```")[1].removeprefix("json")
        parsed = _json.loads(content)
        if parsed.get("category") and parsed["category"] != "none":
            return (parsed["category"], int(parsed.get("severity", 1)),
                    str(parsed.get("quote", "")))
    except Exception:  # noqa: BLE001 - unparseable LLM output is a skip
        return None


async def run_analysis(audio_path: str, ctx, on_event, speed: float = 1.0):
    """Stream audio_path through Universal-Streaming, feeding ctx.detector.

    on_event receives dashboard events: transcript / marker / risk /
    analysis_done.
    """
    pcm, rate = load_pcm16(audio_path, ANALYZE_RATE)
    events: queue.Queue = queue.Queue()

    client = RealTimeTranscriber(
        RealTimeTranscriberOptions(terminate_timeout=10.0),
        api_key=os.environ["ASSEMBLYAI_API_KEY"],
    )
    client.on(RealTimeEvents.Begin, lambda c, e: events.put(("begin", e)))
    client.on(RealTimeEvents.Turn, lambda c, e: events.put(("turn", e)))
    client.on(RealTimeEvents.LLMGatewayResponse,
              lambda c, e: events.put(("llm", e)))
    client.on(RealTimeEvents.Termination, lambda c, e: events.put(("end", e)))
    client.on(RealTimeEvents.Error, lambda c, e: events.put(("error", e)))

    def feed_audio():
        try:
            client.connect(RealTimeParameters(
                speech_model="universal-streaming-english",
                encoding=Encoding.pcm_s16le,
                sample_rate=rate,
                format_turns=True,
                llm_gateway=LLMGatewayConfig(
                    model="claude-sonnet-4-6",
                    messages=[{"role": "user", "content": LLM_TURN_PROMPT}],
                    max_tokens=120,
                ),
            ))
            for chunk, dur in chunk_bytes(pcm, rate):
                client.stream(chunk)
                time.sleep(dur / max(speed, 0.25))
            client.disconnect(terminate=True)
        except Exception as exc:  # noqa: BLE001 - surface to drain loop
            events.put(("error", exc))

    thread = threading.Thread(target=feed_audio, daemon=True)
    thread.start()

    while thread.is_alive() or not events.empty():
        try:
            kind, ev = await asyncio.get_event_loop().run_in_executor(
                None, lambda: events.get(timeout=0.2))
        except queue.Empty:
            continue

        if kind == "begin":
            await on_event({"type": "session_ready", "session_id": str(ev.id)})

        elif kind == "turn":
            text = getattr(ev, "transcript", "") or ""
            final = bool(getattr(ev, "end_of_turn", False))
            if not text:
                continue
            ctx.log.add_transcript("caller", text, final=final)
            markers = ctx.detector.feed(text, speaker="caller")
            await on_event({"type": "transcript", "speaker": "caller",
                            "text": text, "final": final})
            for m in markers:
                ctx.log.log("marker", **m.to_dict())
                await on_event({"type": "marker", **m.to_dict()})
            if markers:
                await on_event({"type": "risk", **ctx.detector.snapshot()})

        elif kind == "llm":
            hit = _parse_llm_marker(getattr(ev, "data", {}) or {})
            if hit:
                cat, sev, quote = hit
                m = ctx.detector.agent_flag(cat, quote, sev,
                                            source="llm_gateway")
                if m:
                    ctx.log.log("marker", **m.to_dict())
                    await on_event({"type": "marker", **m.to_dict()})
                    await on_event({"type": "risk", **ctx.detector.snapshot()})

        elif kind == "end":
            await on_event({"type": "analysis_done",
                            "audio_seconds": getattr(ev, "audio_duration_seconds", None)})

        elif kind == "error":
            await on_event({"type": "error", "detail": str(ev)})
