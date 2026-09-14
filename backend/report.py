"""Post-call threat report.

Two data sources, both AssemblyAI:
  1. Async transcribe of the caller-side audio (when available) with Speech
     Understanding: speaker labels, sentiment, entities, highlights, IAB
     topics, PII redaction.
  2. LLM Gateway (aai.Lemur) over the captured transcript text for a
     structured JSON verdict.

Output: reports/{call_id}.report.json
"""

import json
import os
from pathlib import Path

import assemblyai as aai
import httpx

LLM_GATEWAY_URL = "https://llm-gateway.assemblyai.com/v1/chat/completions"
LLM_GATEWAY_MODEL = os.environ.get("LLM_GATEWAY_MODEL", "claude-sonnet-4-6")

VERDICT_PROMPT = """\
You are a fraud analyst. Given this phone-call transcript and the detector \
markers already fired, produce a JSON verdict (and nothing else) with keys:
  scam_type        (e.g. irs_impersonation, tech_support, grandparent_emergency,
                    bank_fraud, lottery_prize, generic_scam, legitimate)
  risk_score       (0-100 integer)
  confidence       (0-1 float)
  caller_claimed_identity  (string)
  requested_actions        (array of strings — what the caller asked for)
  money_amounts    (array of strings)
  red_flags        (array of strings)
  recommended_actions     (array of strings for the family)
  summary          (2-3 sentences)

Transcript:
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text.removeprefix("json")
    return json.loads(text)


def generate_report(ctx, audio_path: str | None = None) -> dict:
    """Blocking; run via asyncio.to_thread."""
    aai.settings.api_key = os.environ["ASSEMBLYAI_API_KEY"]
    detector = ctx.detector
    snap = detector.snapshot()
    transcript_text = ctx.log.transcript_text()

    understanding = {}
    if audio_path and Path(audio_path).exists():
        config = aai.TranscriptionConfig(
            speaker_labels=True,
            sentiment_analysis=True,
            entity_detection=True,
            auto_highlights=True,
            iab_categories=True,
            redact_pii=True,
        )
        t = aai.Transcriber().transcribe(audio_path, config)
        if t.status == aai.TranscriptStatus.completed:
            understanding = {
                "summary": getattr(t, "summary", None),
                "highlights": [
                    {"text": h.text, "count": h.count}
                    for h in (t.auto_highlights.results if t.auto_highlights else [])
                ][:10],
                "entities": [
                    {"text": e.text, "type": e.entity_type}
                    for e in (t.entities or [])
                ][:20],
                "iab_categories": (
                    t.iab_categories.summary if t.iab_categories else {}
                ),
                "sentiment": [
                    {"text": s.text, "sentiment": s.sentiment}
                    for s in (t.sentiment_analysis or [])
                ][:10],
                "redacted_text": getattr(t, "text", None),
            }

    markers_block = "\n".join(
        f"- [{m.category}] {m.quote} (weight {m.weight}, via {m.source})"
        for m in detector.markers
    ) or "- none"

    verdict = {}
    try:
        resp = httpx.post(
            LLM_GATEWAY_URL,
            headers={"Authorization": os.environ["ASSEMBLYAI_API_KEY"],
                     "Content-Type": "application/json"},
            json={
                "model": LLM_GATEWAY_MODEL,
                "messages": [{"role": "user", "content":
                              VERDICT_PROMPT + transcript_text
                              + "\n\nDetector markers already fired:\n"
                              + markers_block}],
                "max_tokens": 1200,
                "temperature": 0.2,
            },
            timeout=60,
        )
        resp.raise_for_status()
        verdict = _extract_json(resp.json()["choices"][0]["message"]["content"])
    except Exception as exc:  # noqa: BLE001 - report must still render
        verdict = {"error": f"LLM Gateway failed: {exc}"}

    report = {
        "call_id": ctx.log.call_id,
        "mode": ctx.log.mode,
        "detector": snap,
        "markers": [m.to_dict() for m in detector.markers],
        "trusted": detector.trusted,
        "passed_to_family": getattr(ctx, "passed", False),
        "understanding": understanding,
        "verdict": verdict,
        "transcript": transcript_text,
    }
    out = Path(ctx.log.path).with_suffix(".report.json")
    out.write_text(json.dumps(report, indent=2))
    return report
