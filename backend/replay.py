"""Replay mode: run the bundled sample call through the dashboard live.

Streams the recorded audio to the UI (50ms chunks, real-time paced),
reveals each transcript line as partials while it plays, and feeds caller
lines through the rule detector — the full marker/risk/verdict story with
no API key required. Sample line timings come from samples/*.lines.json
(written by scripts/make_sample.py).
"""

import asyncio
import base64
import json
from pathlib import Path

from audio import chunk_bytes, load_pcm16

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"


async def _play_span(pcm: bytes, rate: int, t0: float, t1: float,
                     emit, speed: float, who: str):
    seg = pcm[int(t0 * rate) * 2 : int(t1 * rate) * 2]
    for piece, dur in chunk_bytes(seg, rate):
        await emit({"type": "call_audio", "speaker": who,
                    "audio": base64.b64encode(piece).decode()})
        await asyncio.sleep(dur / speed)


async def _play_line(ctx, emit, pcm: bytes, rate: int, line: dict,
                     speed: float):
    """Stream one line's audio; reveal the transcript as partials along the
    way, then the final line + detection for caller speech."""
    dur = line["end_s"] - line["start_s"]
    spk = line["speaker"]
    words = line["text"].split()
    marks = sorted({int(len(words) * f) for f in (0.4, 0.75)
                    if 0 < int(len(words) * f) < len(words)})
    seg = pcm[int(line["start_s"] * rate) * 2 : int(line["end_s"] * rate) * 2]
    pos = 0.0
    mi = 0
    for piece, d in chunk_bytes(seg, rate):
        if ctx.should_end:
            return
        await emit({"type": "call_audio", "speaker": spk,
                    "audio": base64.b64encode(piece).decode()})
        pos += d
        await asyncio.sleep(d / speed)
        while mi < len(marks) and pos >= dur * marks[mi] / len(words):
            await emit({"type": "transcript", "speaker": spk,
                        "text": " ".join(words[:marks[mi]]), "final": False})
            mi += 1

    ctx.log.add_transcript(spk, line["text"])
    await emit({"type": "transcript", "speaker": spk,
                "text": line["text"], "final": True})

    if spk == "caller":
        markers = ctx.detector.feed(line["text"], speaker="caller")
        for m in markers:
            ctx.log.log("marker", **m.to_dict())
            await emit({"type": "marker", **m.to_dict()})
        if markers:
            await emit({"type": "risk", **ctx.detector.snapshot()})


async def run_replay(ctx, emit, speed: float = 1.0,
                     sample: str = "irs_scam_call.wav"):
    wav = SAMPLES / Path(sample).name
    meta = wav.with_suffix(".lines.json")
    if not wav.exists() or not meta.exists():
        await emit({"type": "error",
                    "detail": f"missing replay assets for {wav.name} "
                              f"(run scripts/make_sample.py)"})
        return
    lines = json.loads(meta.read_text())
    pcm, rate = load_pcm16(str(wav), 24000)
    total = len(pcm) / (rate * 2)

    t = 0.0
    for line in lines:
        if ctx.should_end:
            return
        if line["start_s"] > t:
            await _play_span(pcm, rate, t, line["start_s"],
                             emit, speed, "caller")
        await _play_line(ctx, emit, pcm, rate, line, speed)
        t = line["end_s"]
    if t < total:
        await _play_span(pcm, rate, t, total, emit, speed, "caller")
