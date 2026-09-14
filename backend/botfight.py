"""Botfight mode: a scripted scammer Voice Agent session is piped directly
into the firewall session. Two AIs on one call; the audience hears both and
the dashboard scores the scammer in real time. Deterministic demo — no
phone lines, no human needed.

Audio routing:
  scammer.reply.audio  -> firewall.send_audio + browser speakers
  firewall.reply.audio -> scammer.send_audio + browser speakers
Transcripts shown from the firewall session only (its transcript.user IS
the scammer), so nothing is double-rendered.
"""

import asyncio

from agent_session import AgentSession, CallContext
from personas import SCAMMER_PROMPT, VOICES


async def run_botfight(ctx: CallContext, on_event, on_audio,
                       duration_cap: float = 180.0):
    scammer_ctx = CallContext(ctx.detector.__class__(), ctx.log)  # own detector, unused

    async def scammer_event(ev):  # swallow scammer-side events
        if ev.get("type") == "error":
            await on_event(ev)

    async def firewall_event(ev):
        await on_event(ev)

    async def scammer_audio(pcm: bytes):
        await firewall.send_audio(pcm)
        await on_audio(pcm, "scammer")

    async def firewall_audio(pcm: bytes):
        await scammer.send_audio(pcm)
        await on_audio(pcm, "firewall")

    from personas import GREETING, SCREENER_PROMPT

    scammer = AgentSession(
        scammer_ctx, SCAMMER_PROMPT, VOICES["scammer"], greeting=None,
        on_event=scammer_event, on_audio=scammer_audio, tools=[])
    firewall = AgentSession(
        ctx, SCREENER_PROMPT, VOICES["screener"], greeting=GREETING,
        on_event=firewall_event, on_audio=firewall_audio)

    await scammer.start()
    await firewall.start()

    try:
        await asyncio.wait_for(
            asyncio.gather(scammer.done.wait(), firewall.done.wait(),
                           return_exceptions=True),
            timeout=duration_cap,
        )
    except asyncio.TimeoutError:
        await on_event({"type": "botfight_timeout", "cap_s": duration_cap})
    finally:
        await scammer.close()
        await firewall.close()
