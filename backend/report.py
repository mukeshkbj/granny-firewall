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
import re
import time
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


RECOMMENDED = {
    "payment_vector": "No legitimate agency takes gift cards, crypto, or "
                      "wire transfers. Any caller who demands one is a scammer.",
    "impersonation": "Real agencies confirm enforcement by mail, not phone. "
                     "Verify independently using the official published number.",
    "isolation": "A caller who says 'tell no one' is exactly who the family "
                 "should hear about.",
    "credential_phishing": "No bank or agency ever asks for card numbers, PINs, "
                           "or security codes by phone.",
    "urgency_threat": "Arrest warrants are never settled over the phone. "
                      "Pressure to act fast is itself the red flag.",
    "too_good_to_be_true": "Unsolicited prizes and refunds that need a fee or "
                           "card purchase are always fraudulent.",
    "grandparent_emergency": "Hang up and call the family member on their known "
                             "number before believing any emergency claim.",
}


def local_verdict(ctx) -> dict:
    """Rule-based verdict when no AssemblyAI key is configured. Pulls the
    story straight from the detector and the caller's own words."""
    det = ctx.detector
    snap = det.snapshot()
    caller_lines = [t["text"] for t in ctx.log.transcript
                    if t["speaker"] == "caller"]
    caller_text = " ".join(caller_lines)

    identity = None
    # scammers announce themselves with an org: "this is X from the Y" —
    # prefer that over an innocent "this is Ethel" from the callee
    m = re.search(r"this is ([^.,]{3,60}?)\s+(?:from|calling from|with)\s+(?:the )?([^.,]{3,50})",
                  caller_text, re.IGNORECASE)
    if m:
        identity = f"{m.group(1).strip()}, {m.group(2).strip()}"
    else:
        m = re.search(r"this is ([^.,]{3,60}?)(?:\s+calling|[.,]|$)",
                      caller_text, re.IGNORECASE)
        if m:
            identity = m.group(1).strip()

    money = sorted(set(
        re.findall(r"\$\s?\d[\d,]*"
                   r"|\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
                   r"\s+(?:gift\s?)?cards?\b"
                   r"|\b(?:\w+\s+)?(?:hundred|thousand)\s+dollars?\b",
                   caller_text, re.IGNORECASE)))

    actions = [s.strip() for s in re.split(r"(?<=[.!?])\s+", caller_text)
               if re.search(r"\b(must|need to|go to|read me|buy|stay on|"
                            r"do not|don't|act within)\b", s, re.IGNORECASE)][:5]

    dur = round(time.time() - ctx.log.started_at)
    score = snap["score"]
    scam = {
        "irs_impersonation": "IRS impersonation",
        "tech_support": "tech-support scam",
        "grandparent_emergency": "grandparent-emergency scam",
        "bank_fraud": "bank-fraud scam",
        "lottery_prize": "lottery/prize scam",
        "generic_scam": "common phone-scam playbook",
        "legitimate_or_unknown": "legitimate call",
    }.get(snap["scam_type"], snap["scam_type"].replace("_", " "))

    recommended = [RECOMMENDED[c] for c in snap["categories_hit"]
                   if c in RECOMMENDED]
    if det.markers:
        recommended.insert(0, f"This call kept the scammer on the line for "
                              f"{dur}s. That time came out of their dial "
                              f"list, not your family's day.")
    recommended.append("Report the number to reportfraud.ftc.gov and warn "
                       "neighbors or family who might get the same call.")

    summary = (
        f"The caller {('claimed to be ' + identity) if identity else 'posed as an authority figure'}. "
        f"{len(det.markers)} scam signal{'s' if len(det.markers) != 1 else ''} "
        f"fired across {len(caller_lines)} caller turn{'s' if len(caller_lines) != 1 else ''} "
        f"and risk reached {score:.0f}/100. "
        f"This matches the {scam} playbook." if det.markers else
        "No scam signals fired — the call looks clean, but the recording "
        "is worth a manual skim anyway."
    )

    return {
        "scam_type": snap["scam_type"],
        "risk_score": int(score),
        "confidence": round(min(0.95, 0.45 + 0.07 * len(det.markers)), 2),
        "caller_claimed_identity": identity or "unidentified",
        "requested_actions": actions,
        "money_amounts": money,
        "red_flags": [f"{m.label}: “{m.quote}”" for m in det.markers][:8],
        "recommended_actions": recommended,
        "summary": summary,
        "source": "local_rules",
    }


def generate_report(ctx, audio_path: str | None = None) -> dict:
    """Blocking; run via asyncio.to_thread. Works without an API key —
    falls back to the rule-based verdict."""
    key = os.environ.get("ASSEMBLYAI_API_KEY")
    detector = ctx.detector
    snap = detector.snapshot()
    transcript_text = ctx.log.transcript_text()

    understanding = {}
    if key and audio_path and Path(audio_path).exists():
        aai.settings.api_key = key
        config = aai.TranscriptionConfig(
            speaker_labels=True,
            sentiment_analysis=True,
            entity_detection=True,
            auto_highlights=True,
            iab_categories=True,
            redact_pii=True,
            redact_pii_policies=[
                aai.PIIRedactionPolicy.credit_card_number,
                aai.PIIRedactionPolicy.credit_card_cvv,
                aai.PIIRedactionPolicy.us_social_security_number,
                aai.PIIRedactionPolicy.account_number,
                aai.PIIRedactionPolicy.phone_number,
                aai.PIIRedactionPolicy.number_sequence,
                aai.PIIRedactionPolicy.date_of_birth,
            ],
            redact_pii_sub=aai.PIISubstitutionPolicy.entity_name,
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
    if not key:
        verdict = local_verdict(ctx)
    else:
        try:
            resp = httpx.post(
                LLM_GATEWAY_URL,
                headers={"Authorization": key,
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
            verdict = _extract_json(
                resp.json()["choices"][0]["message"]["content"])
        except Exception as exc:  # noqa: BLE001 - report must still render
            verdict = local_verdict(ctx)
            verdict["error"] = "verdict service unavailable — local rules used"

    report = {
        "call_id": ctx.log.call_id,
        "mode": ctx.log.mode,
        "duration_s": round(time.time() - ctx.log.started_at),
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
