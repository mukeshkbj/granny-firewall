"""Scam signature taxonomy: weighted regex patterns per category.

Each pattern carries the category's weight; a single transcript turn can fire
multiple patterns but each category is deduped per time window by the detector.
"""

CATEGORIES = {
    "impersonation": {
        "weight": 25,
        "label": "Impersonation",
        "patterns": [
            r"\birs\b", r"internal revenue", r"social security (administration|office|number)",
            r"fraud (department|division|team)", r"tax (crime|enforcement)",
            r"microsoft (support|technician|windows)", r"apple (support|care)",
            r"(sheriff|police) (department|office)", r"federal (agent|officer|bureau)",
            r"bank('s)? fraud", r"amazon (support|security|billing)", r"geek squad",
            r"customs (officer|department)", r"border patrol",
        ],
    },
    "urgency_threat": {
        "weight": 15,
        "label": "Urgency & threats",
        "patterns": [
            r"arrest warrant", r"within 24 hours", r"final notice", r"legal action",
            r"will be arrested", r"immediately", r"right now", r"suspended",
            r"frozen (account|assets)", r"law enforcement", r"magistrate",
            r"act (now|immediately|fast)", r"urgent(ly)?", r"limited time",
        ],
    },
    "payment_vector": {
        "weight": 35,
        "label": "Payment demanded",
        "patterns": [
            r"gift ?cards?", r"itunes", r"google play", r"steam card", r"target card",
            r"wire (transfer|the money)", r"western union", r"moneygram",
            r"bitcoin|crypto(currency)?|usdt|ethereum", r"zelle|venmo|cash ?app",
            r"payment kiosk", r"pay now", r"prepaid card", r"reloadable",
            r"apple pay", r"bank transfer", r"deposit (the )?(check|cheque)",
        ],
    },
    "credential_phishing": {
        "weight": 30,
        "label": "Credential phishing",
        "patterns": [
            r"one[- ]time (pass)?code", r"\botp\b", r"verification code",
            r"verify your (account|identity|social)", r"social security number",
            r"account (number|details|password)", r"confirm your (details|identity)",
            r"remote (access|desktop)", r"anydesk|teamviewer", r"security code",
            r"mother'?s maiden", r"date of birth", r"pin (number|code)",
        ],
    },
    "isolation": {
        "weight": 20,
        "label": "Isolation",
        "patterns": [
            r"don'?t (tell|inform) (your )?(family|anyone|children|son|daughter)",
            r"stay on the (line|phone)", r"do not hang up", r"keep this (confidential|between us)",
            r"this is (a )?sensitive (matter|case)", r"don'?t discuss",
            r"not allowed to (tell|speak)", r"secrecy",
        ],
    },
    "too_good_to_be_true": {
        "weight": 15,
        "label": "Too good to be true",
        "patterns": [
            r"you('ve| have) won", r"lottery", r"sweepstakes", r"prize (money|fund)",
            r"congratulations", r"free (vacation|gift|money)", r"refund (of|owed|due)",
            r"unclaimed (money|funds|property)", r"inheritance", r"lucky winner",
        ],
    },
    "grandparent_emergency": {
        "weight": 25,
        "label": "Family emergency",
        "patterns": [
            r"(it'?s|this is) (me,? )?your (grand)?(son|daughter|child)",
            r"in (jail|custody|an accident|the hospital)", r"bail (money|bond)",
            r"car (accident|crash)", r"stranded", r"need (your )?help (please|urgently)",
            r"arrested", r"don'?t tell (mom|dad|my parents)",
        ],
    },
}

# Scam-type inference: first matching rule wins, in priority order.
SCAM_TYPE_RULES = [
    ("irs_impersonation", ["impersonation", "urgency_threat", "payment_vector"]),
    ("tech_support", ["impersonation", "credential_phishing"]),
    ("grandparent_emergency", ["grandparent_emergency", "isolation"]),
    ("bank_fraud", ["impersonation", "credential_phishing", "urgency_threat"]),
    ("lottery_prize", ["too_good_to_be_true", "payment_vector"]),
]

RISK_LEVELS = [
    (85, "critical", "End call immediately"),
    (60, "high", "Likely scam — engage waster persona"),
    (30, "elevated", "Suspicious — keep screening"),
    (0, "low", "Probably legitimate"),
]


def risk_level(score: float) -> tuple[str, str]:
    for threshold, level, action in RISK_LEVELS:
        if score >= threshold:
            return level, action
    return "low", "Probably legitimate"


def infer_scam_type(categories_hit: set[str]) -> str:
    for scam_type, required in SCAM_TYPE_RULES:
        if set(required).issubset(categories_hit):
            return scam_type
    if categories_hit:
        return "generic_scam"
    return "legitimate_or_unknown"
