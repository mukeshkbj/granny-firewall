"""FastAPI app: dashboard WS, call control, analyze upload, botfight.

Run: uvicorn server:app --reload --port 8000   (from backend/)
Frontend dev: cd frontend && npm run dev     (vite proxies /ws + /api)
"""

import asyncio
import base64
import json
from pathlib import Path

from agent_session import AgentSession, CallContext
from call_log import CallLog
from detector import Detector
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from hub import hub
from personas import GREETING, SCREENER_PROMPT, VOICES
from report import generate_report

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="Granny Firewall")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
SAMPLES.mkdir(exist_ok=True)


class CallManager:
    """One active call at a time (hackathon scope)."""

    def __init__(self):
        self.ctx: CallContext | None = None
        self.session: AgentSession | None = None
        self.task: asyncio.Task | None = None
        self.caller_pcm = bytearray()   # saved for the report's audio
        self.mode: str | None = None

    def new_ctx(self, mode: str) -> CallContext:
        self.mode = mode
        self.caller_pcm = bytearray()
        self.ctx = CallContext(Detector(), CallLog(mode))
        return self.ctx

    async def emit(self, event: dict):
        await hub.broadcast(event)

    async def stop(self):
        if self.task:
            self.task.cancel()
        if self.session:
            await self.session.close()
        if self.ctx:
            self.ctx.log.end()
            await hub.broadcast({"type": "call_ended",
                                 "call_id": self.ctx.log.call_id})


manager = CallManager()


# ---------- dashboard ----------------------------------------------------

@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket):
    await hub.connect(ws)
    try:
        if manager.ctx:
            await ws.send_json({"type": "state",
                                "mode": manager.mode,
                                "persona": manager.ctx.persona,
                                "risk": manager.ctx.detector.snapshot()})
        while True:
            await ws.receive_text()   # keepalive; client sends nothing
    except WebSocketDisconnect:
        hub.disconnect(ws)


# ---------- live screen mode (browser mic) --------------------------------

@app.websocket("/ws/call")
async def ws_call(ws: WebSocket):
    """Binary frames from browser = caller PCM16 24k. Server sends binary
    frames back = agent reply audio (same format)."""
    await ws.accept()
    try:
        ctx = manager.new_ctx("live")
        await hub.broadcast({"type": "call_started", "mode": "live",
                             "call_id": ctx.log.call_id})

        async def on_agent_audio(pcm: bytes):
            await ws.send_bytes(pcm)

        manager.session = AgentSession(
            ctx, SCREENER_PROMPT, VOICES["screener"], GREETING,
            on_event=manager.emit, on_audio=on_agent_audio)
        await manager.session.start()

        from audio import resample_pcm16, wav_bytes
        rate = 24000
        while True:
            msg = await ws.receive()
            if msg.get("bytes"):
                pcm = resample_pcm16(msg["bytes"], rate, 24000)
                manager.caller_pcm += pcm
                await manager.session.send_audio(pcm)
            elif msg.get("text"):
                try:
                    ctrl = json.loads(msg["text"])
                except ValueError:
                    ctrl = {}
                if ctrl.get("type") == "start" and ctrl.get("rate"):
                    rate = int(ctrl["rate"])
                elif ctrl.get("type") == "stop" or msg["text"] == "stop":
                    break
            if ctx.should_end:
                break
    except WebSocketDisconnect:
        pass
    finally:
        # keep caller audio for the post-call Speech Understanding pass
        if manager.caller_pcm and manager.ctx:
            wav = ROOT / "reports" / f"{manager.ctx.log.call_id}_caller.wav"
            wav.write_bytes(wav_bytes(bytes(manager.caller_pcm), 24000))
            manager.ctx.caller_wav = str(wav)
        await manager.stop()


# ---------- analyze mode --------------------------------------------------

@app.post("/api/analyze")
async def analyze(file: UploadFile, speed: float = 1.0):
    await manager.stop()
    dest = SAMPLES / f"upload_{Path(file.filename).name}"
    dest.write_bytes(await file.read())

    ctx = manager.new_ctx("analyze")
    await hub.broadcast({"type": "call_started", "mode": "analyze",
                         "call_id": ctx.log.call_id, "file": file.filename})

    from stream_session import run_analysis

    async def run():
        try:
            await run_analysis(str(dest), ctx, manager.emit, speed=speed)
        finally:
            ctx.log.end()
            report = await asyncio.to_thread(generate_report, ctx, str(dest))
            await hub.broadcast({"type": "report", "report": report})

    manager.task = asyncio.create_task(run())
    return {"call_id": ctx.log.call_id}


@app.get("/api/samples")
async def list_samples():
    return sorted(p.name for p in SAMPLES.iterdir()
                  if p.suffix.lower() in {".wav", ".mp3", ".ogg", ".flac", ".m4a"})


@app.post("/api/analyze_sample")
async def analyze_sample(name: str, speed: float = 1.0):
    dest = SAMPLES / Path(name).name          # path-safe
    if not dest.exists():
        return {"error": f"unknown sample: {name}"}
    await manager.stop()
    ctx = manager.new_ctx("analyze")
    await hub.broadcast({"type": "call_started", "mode": "analyze",
                         "call_id": ctx.log.call_id, "file": dest.name})

    from stream_session import run_analysis

    async def run():
        try:
            await run_analysis(str(dest), ctx, manager.emit, speed=speed)
        finally:
            ctx.log.end()
            report = await asyncio.to_thread(generate_report, ctx, str(dest))
            await hub.broadcast({"type": "report", "report": report})

    manager.task = asyncio.create_task(run())
    return {"call_id": ctx.log.call_id}


# ---------- botfight mode -------------------------------------------------

@app.post("/api/botfight")
async def botfight(cap_s: float = 180.0):
    await manager.stop()
    ctx = manager.new_ctx("botfight")
    await hub.broadcast({"type": "call_started", "mode": "botfight",
                         "call_id": ctx.log.call_id})

    from botfight import run_botfight

    async def on_audio(pcm: bytes, who: str):
        await hub.broadcast({"type": "call_audio", "speaker": who,
                             "audio": base64.b64encode(pcm).decode()})

    async def run():
        try:
            await run_botfight(ctx, manager.emit, on_audio, duration_cap=cap_s)
        finally:
            ctx.log.end()
            report = await asyncio.to_thread(generate_report, ctx)
            await hub.broadcast({"type": "report", "report": report})

    manager.task = asyncio.create_task(run())
    return {"call_id": ctx.log.call_id}


# ---------- control + reports ---------------------------------------------

@app.post("/api/call/stop")
async def stop_call():
    await manager.stop()
    return {"ok": True}


@app.post("/api/report")
async def make_report():
    """Generate report for the just-ended call (live mode path)."""
    if not manager.ctx:
        return {"error": "no call"}
    report = await asyncio.to_thread(
        generate_report, manager.ctx, getattr(manager.ctx, "caller_wav", None))
    await hub.broadcast({"type": "report", "report": report})
    return report


@app.get("/api/report/{call_id}")
async def get_report(call_id: str):
    p = ROOT / "reports" / f"{call_id}.report.json"
    if not p.exists():
        return {"error": "not found"}
    return FileResponse(p)


# ---------- STRETCH: twilio inbound ----------------------------------------

@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    from urllib.parse import urlparse

    from twilio_bridge import voice_webhook
    form = await request.form()
    host = request.headers.get("host", "localhost:8008")
    scheme = "wss" if urlparse(str(request.url)).scheme == "https" else "ws"
    return voice_webhook(form.get("From", ""), f"{scheme}://{host}/twilio/stream")


@app.websocket("/twilio/stream")
async def twilio_stream(ws: WebSocket):
    from twilio_bridge import handle_stream
    ctx = manager.new_ctx("twilio")
    await hub.broadcast({"type": "call_started", "mode": "twilio",
                         "call_id": ctx.log.call_id})
    try:
        await handle_stream(ws, ctx, manager.emit)
    except WebSocketDisconnect:
        pass
    finally:
        ctx.log.end()
        await hub.broadcast({"type": "call_ended",
                             "call_id": ctx.log.call_id})


# ---------- static frontend (production build) ----------------------------

dist = ROOT / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
