import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from detector import Detector
from signatures import infer_scam_type

TS = 1_000_000.0


def feed(det, texts):
    markers = []
    for i, t in enumerate(texts):
        markers += det.feed(t, ts=TS + i * 5)
    return markers


def test_irs_scam_scores_high():
    d = Detector()
    feed(d, [
        "This is Officer Miller from the IRS internal revenue service.",
        "A warrant for your arrest will be issued within 24 hours.",
        "You must pay immediately with Apple gift cards, five hundred dollars each.",
        "Stay on the line and do not tell your family about this.",
    ])
    assert d.risk_score >= 60
    assert d.snapshot()["scam_type"] == "irs_impersonation"
    cats = d.snapshot()["categories_hit"]
    assert {"impersonation", "payment_vector", "isolation"} <= set(cats)


def test_legitimate_caller_stays_low():
    d = Detector()
    feed(d, [
        "Hi, this is Carol from the pharmacy, your prescription is ready.",
        "You can pick it up any time today before nine.",
        "No rush at all, just wanted to let you know. Have a great day!",
    ])
    assert d.risk_score == 0
    assert d.snapshot()["level"] == "low"


def test_agent_speech_is_not_flagged():
    d = Detector()
    markers = d.feed("You mentioned gift cards — can you explain why?",
                     ts=TS, speaker="agent")
    assert markers == []
    assert d.risk_score == 0


def test_codeword_clamps_score():
    d = Detector()
    feed(d, ["This is the fraud department calling about your account."])
    assert d.risk_score > 0
    assert d.verify_codeword("Blueberry!", "blueberry")
    assert d.risk_score <= 15
    # no further escalation while trusted
    feed(d, ["Anyway, about that gift card idea at the store..."])
    assert d.risk_score <= 15


def test_wrong_codeword_rejected():
    d = Detector()
    assert not d.verify_codeword("strawberry", "blueberry")
    assert not d.trusted


def test_agent_flag_merges_into_score():
    d = Detector()
    m = d.agent_flag("credential_phishing", "read me your verification code",
                     severity=3, ts=TS)
    assert m and m.source == "agent"
    assert "credential_phishing" in d.snapshot()["categories_hit"]


def test_decay_reduces_score():
    d = Detector()
    feed(d, ["You have won a lottery prize, congratulations!"])
    first = d.risk_score
    assert first > 0
    # 200s of clean speech later
    d.feed("Nice weather today.", ts=TS + 300)
    assert d.risk_score == 0


def test_dedup_same_signature_in_window():
    d = Detector()
    feed(d, ["gift cards gift cards gift cards"])
    n = len(d.markers)
    d.feed("I said gift cards!", ts=TS + 3)
    assert len(d.markers) == n  # deduped


def test_scam_type_inference():
    assert infer_scam_type({"impersonation", "urgency_threat",
                            "payment_vector"}) == "irs_impersonation"
    assert infer_scam_type({"grandparent_emergency", "isolation"}) == "grandparent_emergency"
    assert infer_scam_type(set()) == "legitimate_or_unknown"
