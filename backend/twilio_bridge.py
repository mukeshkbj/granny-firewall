"""STRETCH (M7): Twilio inbound screening.

Flow:
  POST /twilio/voice   Twilio webhook on inbound call. If the caller is on
                       TWILIO_ALLOWLIST → <Dial> straight to family (no
                       screening). Otherwise → <Connect><Stream> to our WS.
  WS   /twilio/stream  Bidirectional Media Stream. Twilio audio is G.711
                       μ-law 8kHz; the Voice Agent API supports audio/pcmu
                       natively, so bytes flow through untouched both ways.
  pass_to_family       Calls the Twilio REST API to redirect the live call
                       into <Dial>FAMILY_REAL_NUMBER</Dial>.

Setup: point a Twilio number's voice webhook at
https://<your-host>/twilio/voice (ngrok for local demo). Env:
TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, FAMILY_REAL_NUMBER, TWILIO_ALLOWLIST
(comma-separated E.164 numbers that skip screening).
"""

import base64
import json
import os

import httpx
from agent_session import AgentSession, CallContext
from fastapi import WebSocket
from fastapi.responses import Response
from personas import GREETING, SCREENER_PROMPT, VOICES

TWILIO_API = "https://api.twilio.com/2010-04-01"


def _allowlist() -> set[str]:
    return {n.strip() for n in os.environ.get("TWILIO_ALLOWLIST", "").split(",")
            if n.strip()}


def twiml(body: str) -> Response:
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>',
                    media_type="application/xml")


def voice_webhook(from_number: str, ws_url: str) -> Response:
    """TwiML for an inbound call. Allowlisted numbers bypass the firewall."""
    family = os.environ.get("FAMILY_REAL_NUMBER", "")
    if from_number in _allowlist() and family:
        return twiml(f'<Dial callerId="{from_number}">{family}</Dial>')
    if not os.environ.get("ASSEMBLYAI_API_KEY"):
        return twiml(
            '<Say voice="alice">You have reached Granny Firewall, a scam '
            'call screening demo. The voice agent is not configured yet, so '
            'this call cannot be screened. Goodbye.</Say><Hangup/>')
    return twiml(
        f'<Connect><Stream url="{ws_url}">'
        f'<Parameter name="from" value="{from_number}"/></Stream></Connect>')


async def transfer_to_family(call_sid: str) -> bool:
    """Redirect the in-progress call to the real family number."""
    sid, token = os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN")
    family = os.environ.get("FAMILY_REAL_NUMBER")
    if not (sid and token and family):
        return False
    async with httpx.AsyncClient(auth=(sid, token)) as c:
        r = await c.post(
            f"{TWILIO_API}/Accounts/{sid}/Calls/{call_sid}.json",
            data={"Twiml": f"<Response><Dial>{family}</Dial></Response>"},
            timeout=10)
        return r.status_code == 200


async def handle_stream(ws: WebSocket, ctx: CallContext, on_event):
    """Relay one Twilio Media Stream <-> one Voice Agent session (pcmu)."""
    await ws.accept()
    stream_sid = call_sid = None
    caller = "unknown"

    async def on_agent_audio(mulaw: bytes):
        if stream_sid:
            await ws.send_text(json.dumps({
                "event": "media", "streamSid": stream_sid,
                "media": {"payload": base64.b64encode(mulaw).decode()}}))

    async def emit(ev):
        if ev.get("type") == "interrupted" and stream_sid:
            # drop Twilio's queued audio so the agent stops talking instantly
            await ws.send_text(json.dumps({"event": "clear",
                                           "streamSid": stream_sid}))
        await on_event(ev)

    session = AgentSession(ctx, SCREENER_PROMPT, VOICES["screener"], GREETING,
                           on_event=emit, on_audio=on_agent_audio,
                           input_encoding="audio/pcmu",
                           output_encoding="audio/pcmu")

    try:
        async for raw in ws.iter_text():
            msg = json.loads(raw)
            ev = msg.get("event")
            if ev == "start":
                stream_sid = msg["start"]["streamSid"]
                call_sid = msg["start"].get("callSid")
                caller = (msg["start"].get("customParameters") or {}
                          ).get("from", "unknown")
                ctx.log.log("twilio_start", caller=caller, call_sid=call_sid)
                ctx.bridge = lambda cs=call_sid: transfer_to_family(cs)
                await session.start()
            elif ev == "media":
                await session.send_audio(base64.b64decode(msg["media"]["payload"]))
            elif ev == "stop":
                break
            if ctx.should_end:
                break
    finally:
        await session.close()
