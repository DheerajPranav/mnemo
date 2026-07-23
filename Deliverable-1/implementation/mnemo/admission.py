"""
admission.py — the write path. [M2]

    admit(repo, record, seq)  =  PII-gate  ->  extract typed fact  ->  persist  ->
                                 resolve conflicts on the WRITE path (ADR-001)

Two invariants live here:
  I2 — PII is a HARD precondition: blocked content leaves zero trace (checked first, before any write).
  I3 — conflict resolution happens on the write path: when a new fact arrives for an existing
       (account, subject), the loser is marked invalidated *now*, so the ranker is only ever handed
       currently-valid facts and a stale fact can never be a candidate (closes F4).

SUPERSESSION RULE — see `_supersedes`. This is the one design knob the M3 read-path gate stresses.
"""
from dataclasses import dataclass, field
from typing import List, Tuple

from . import extraction, pii_gate


@dataclass
class AdmitResult:
    id: str
    stored: bool
    reason: str = "admitted"
    pii_entities: List[Tuple[str, str]] = field(default_factory=list)
    invalidated: List[str] = field(default_factory=list)     # existing ids this admit superseded
    admitted_stale: bool = False                             # new fact arrived already-superseded


def _supersedes(a_at, a_seq, b_at, b_seq):
    """Does fact A supersede fact B for the same (account, subject)?

    v2 (M3 recovery): lexicographic on (recorded_at, ingestion seq). v1 compared time only — the
    natural reading of ADR-001 — but left the same-day flip unresolved: the SSO pair m005/m006 share
    recorded_at 2025-05-09, so BOTH stayed current and the inverted opinion ("we don't need SSO")
    out-ranked the resolved fact ("put it in — non-negotiable"), failing gate G2 (inversion_failures=1).
    Ingestion order is a monotonic tiebreak: within the same day, the later-recorded utterance wins.
    Documented recovery — see .genesis/checkpoints/M3.md.
    """
    return (a_at, a_seq) > (b_at, b_seq)


def admit(repo, record, seq):
    """Admit one raw record for repo's tenant. Returns an AdmitResult; persists nothing on PII block."""
    text = record["text"]

    # ── I2: hard PII gate FIRST — before extraction, before any write ──
    entities = pii_gate.detect(text)
    if entities:
        # nothing is persisted; we retain only the entity *labels*, never the text (invariant I2)
        return AdmitResult(id=record["id"], stored=False, reason="pii-blocked",
                           pii_entities=[(lbl, "<redacted>") for lbl, _ in entities])

    fields = extraction.extract(record)
    new_at, new_seq = fields["recorded_at"], seq

    # ── I3: resolve conflicts on the write path ──
    conflicts = repo.find_current_conflict(account=fields["account"], subject=fields["subject"])

    repo.add_fact(
        id=fields["id"], account=fields["account"], subject=fields["subject"],
        mem_type=fields["mem_type"], text=fields["text"], recorded_at=fields["recorded_at"],
        seq=seq, actor=fields["actor"], provenance=fields["provenance"],
    )

    invalidated = []
    admitted_stale = False
    for e in conflicts:
        if _supersedes(new_at, new_seq, e.recorded_at, e.seq):
            repo.invalidate(e.id, at=new_at, by=fields["id"])        # existing loses
            invalidated.append(e.id)
        elif _supersedes(e.recorded_at, e.seq, new_at, new_seq):
            repo.invalidate(fields["id"], at=e.recorded_at, by=e.id)  # new arrived already stale
            admitted_stale = True
        # else: tie (equal recorded_at) — v1 resolves nothing; BOTH stay current  (M3 blind spot)

    return AdmitResult(id=fields["id"], stored=True,
                       invalidated=invalidated, admitted_stale=admitted_stale)


def admit_all(repos_by_tenant, records, repo_factory):
    """Admit a batch. `repo_factory(tenant)` returns a TenantRepository bound to that tenant.
    Returns the list of AdmitResults in ingestion order (seq = index)."""
    results = []
    for seq, rec in enumerate(records):
        repo = repos_by_tenant.setdefault(rec["tenant"], repo_factory(rec["tenant"]))
        results.append(admit(repo, rec, seq))
    return results
