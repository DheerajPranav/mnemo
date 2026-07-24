"""
extraction.py — raw record -> typed, validity-stamped fact fields. [M2]

The naive baseline stored raw utterance chunks (design/failure_analysis.md Approach D). Mnemo stores
*typed* facts: a subject slot and a memory kind, so the write path can reason about supersession by
(account, subject) and the ranker can prefer resolved facts over chatter. In production an LLM
extractor proposes the typed fields (validated against a schema — the llmops gate); here the mapping
is deterministic so the loop has a fixed, reproducible oracle (decision D5-DR-001).

Typing untrusted conversation text into constrained fields is also the first line against threat R4
(memory-borne prompt injection): a fact is a (subject, value) slot, not free instructions.
"""

# Slot-valued subjects hold ONE current value, so a newer entry replaces the older (supersession).
# Event-like subjects ACCUMULATE — a call note or thread turn does not contradict the previous one.
# Getting this wrong is F5 (loss): D6/M4 found the write path silently invalidating 31 of 40 memories
# because thread/chatter defaulted to `fact` and therefore superseded each other.
_TYPE_BY_SUBJECT = {
    "crm": "fact",
    "dm": "fact",
    "budget": "fact",
    "residency": "fact",
    "sso": "preference",
    "call_notes": "event",
    "thread": "event",
    "chatter": "event",
}

# Only these types participate in supersession (see admission.admit).
SUPERSEDING_TYPES = frozenset({"fact", "preference"})


def extract(record):
    """Map a raw memory record to the typed fields mnemo persists. Pure/deterministic."""
    subject = record["subject"]
    return {
        "id": record["id"],
        "account": record["account"],
        "subject": subject,
        "mem_type": _TYPE_BY_SUBJECT.get(subject, "fact"),
        "text": record["text"],
        "recorded_at": record["ts"],
        "actor": record.get("user"),
        "provenance": f'{record.get("tenant_name","")}:{record.get("user","")}',
    }
