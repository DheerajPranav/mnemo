"""
pii_gate.py — deterministic, Presidio-style PII recognizer used as a HARD admission gate. [M2]

Invariant **I2**: no memory whose candidate text trips a recognizer is ever persisted — no row, no
embedding, no log payload carrying the text. Closes F11 (sensitive data retained then resurfaced).

Design (ADR-003): deterministic-first. Regex/lexicon recognizers with word boundaries, tuned to fire
on genuine identifiers + health data while NOT tripping on ordinary GTM facts (budgets like "60k",
ISO dates like "2026-04-30", account names). The production gate adds Presidio's ML recognizers
behind these; the deterministic layer is the floor, and the floor is what a review can audit.
"""
import re

# Personal phone: 3 digits, a separator, 4 digits (e.g. 555-0142). The separator is REQUIRED so
# ISO dates (2026-04-30) and money (60k) don't match; \b anchors avoid mid-number hits.
_PHONE = re.compile(r"\b\d{3}[-.\s]\d{4}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# Health / medical condition lexicon (indirect health data is still health data).
_HEALTH = re.compile(
    r"\b(chemotherapy|chemo|cancer|diagnosis|diagnosed|medical leave|"
    r"mental health|disability|HIV|prescription|therapy|illness)\b",
    re.IGNORECASE,
)

_RECOGNIZERS = [
    ("PHONE", _PHONE),
    ("EMAIL", _EMAIL),
    ("US_SSN", _SSN),
    ("HEALTH", _HEALTH),
]


def detect(text):
    """Return a list of (entity_type, matched_span) for every recognizer that fires."""
    hits = []
    for label, pat in _RECOGNIZERS:
        for m in pat.finditer(text or ""):
            hits.append((label, m.group(0)))
    return hits


def is_blocked(text):
    """True iff any recognizer fires — the hard admission precondition (invariant I2)."""
    return bool(detect(text))
