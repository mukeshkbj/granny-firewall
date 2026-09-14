"""Real-time scam-signature detector.

Feeds on caller transcript events and emits marker events. Scoring:
score = sum of weights of distinct categories hit, minus time decay
(2 pts per 10s of clean speech), clamped 0-100. A verified family
codeword clamps the score to <=15.
"""

import re
import time
from dataclasses import asdict, dataclass

from signatures import CATEGORIES, infer_scam_type, risk_level

DECAY_PER_SEC = 0.2        # 2 pts per 10s of clean speech
DEDUP_WINDOW_S = 10.0
TRUSTED_CAP = 15.0


@dataclass
class Marker:
    category: str
    label: str
    quote: str
    weight: int
    source: str              # "rule" | "agent" | "llm_gateway"
    ts: float
    severity: int = 1

    def to_dict(self):
        return asdict(self)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _quote_for(text: str, match: re.Match) -> str:
    """Short context window around the match for the dashboard quote."""
    start = max(0, match.start() - 30)
    end = min(len(text), match.end() + 30)
    quote = text[start:end].strip()
    return ("…" if start > 0 else "") + quote + ("…" if end < len(text) else "")


class Detector:
    def __init__(self):
        self._compiled = {
            cat: [re.compile(p, re.IGNORECASE) for p in cfg["patterns"]]
            for cat, cfg in CATEGORIES.items()
        }
        self.markers: list[Marker] = []
        self.categories_hit: set[str] = set()
        self.trusted = False
        self._score = 0.0
        self._last_ts: float | None = None
        self._recent: dict[tuple[str, str], float] = {}

    # -- inputs -------------------------------------------------------------

    def feed(self, text: str, ts: float | None = None, speaker: str = "caller") -> list[Marker]:
        """Run one transcript chunk through the rule engine.

        Only caller speech is screened — the agent's own utterances legitimately
        contain words like 'gift card' when interrogating.
        """
        ts = time.time() if ts is None else ts
        self._decay(ts)
        if speaker != "caller" or self.trusted:
            return []

        fired = []
        for cat, patterns in self._compiled.items():
            for pat in patterns:
                m = pat.search(text)
                if not m:
                    continue
                key = (cat, _norm(m.group(0)))
                if ts - self._recent.get(key, -1e9) < DEDUP_WINDOW_S:
                    break  # same signature re-firing inside the window → skip
                self._recent[key] = ts
                marker = Marker(
                    category=cat, label=CATEGORIES[cat]["label"],
                    quote=_quote_for(text, m), weight=CATEGORIES[cat]["weight"],
                    source="rule", ts=ts,
                )
                fired.append(marker)
                self._register(marker)
                break  # one hit per category per feed is enough
        return fired

    def agent_flag(self, category: str, quote: str, severity: int = 1,
                   ts: float | None = None, source: str = "agent") -> Marker | None:
        ts = time.time() if ts is None else ts
        self._decay(ts)
        if category not in CATEGORIES or self.trusted:
            return None
        marker = Marker(
            category=category, label=CATEGORIES[category]["label"],
            quote=quote[:120], weight=CATEGORIES[category]["weight"],
            source=source, ts=ts, severity=severity,
        )
        self._register(marker)
        return marker

    def verify_codeword(self, codeword: str, expected: str) -> bool:
        # transcripts carry punctuation/casing noise — compare alphanumeric only
        clean = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
        if clean(codeword) and clean(codeword) == clean(expected):
            self.trusted = True
            self._score = min(self._score, TRUSTED_CAP)
            return True
        return False

    # -- scoring ------------------------------------------------------------

    def _register(self, marker: Marker):
        self.markers.append(marker)
        self.categories_hit.add(marker.category)
        self._recompute()

    def _decay(self, ts: float):
        if self._last_ts is not None:
            self._score = max(0.0, self._score - DECAY_PER_SEC * max(0.0, ts - self._last_ts))
        self._last_ts = ts

    def _recompute(self):
        self._score = min(100.0, sum(CATEGORIES[c]["weight"] for c in self.categories_hit))
        if self.trusted:
            self._score = min(self._score, TRUSTED_CAP)

    @property
    def risk_score(self) -> float:
        return round(self._score, 1)

    def snapshot(self) -> dict:
        level, action = risk_level(self._score)
        return {
            "score": self.risk_score,
            "level": level,
            "action": action,
            "trusted": self.trusted,
            "categories_hit": sorted(self.categories_hit),
            "scam_type": infer_scam_type(self.categories_hit),
            "marker_count": len(self.markers),
        }
