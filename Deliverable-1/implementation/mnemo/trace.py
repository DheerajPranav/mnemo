"""
trace.py — per-request decision traces + fail-closed audit. [M5]

Invariant **I9**: every retrieval writes exactly one `access_log` row BEFORE results are returned; if
the audit write fails, the read **fails closed** (threat R5 — no result without a log row). And every
memory decision is reconstructable for a `request_id` (C9): which facts were candidates, what each
scored, what was dropped and *why*.

The operational question this answers is "why did the assistant not know X?" — `Trace.explain(id)`
localises a memory to the exact stage that dropped it:

    not_a_candidate   — never reached the ranker (superseded / other tenant / deleted / PII-blocked)
    below_threshold   — ranked, but lexical relevance under the abstain bar
    not_grounded      — cleared threshold but belongs to another account (cannot answer alone)
    deduped           — a higher-ranked fact already filled its (account, subject) slot
    budget_dropped    — would have exceeded the token budget
    injected          — made it into the final context
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import retrieval, ranking, injection


class AuditWriteError(RuntimeError):
    """Raised when the audit log cannot be written. The read must fail closed (R5)."""


@dataclass
class Trace:
    request_id: str
    tenant_id: str
    account: str
    query: str
    candidate_ids: List[str] = field(default_factory=list)
    scores: Dict[str, dict] = field(default_factory=dict)      # id -> {score, lexical, account}
    stages: Dict[str, str] = field(default_factory=dict)       # id -> stage that decided its fate
    injected_ids: List[str] = field(default_factory=list)
    tokens_used: int = 0
    abstained: bool = False
    notes: List[str] = field(default_factory=list)

    def explain(self, memory_id: str) -> str:
        """Which stage decided this memory's fate for this request."""
        return self.stages.get(memory_id, "not_a_candidate")

    def as_dict(self):
        return {
            "request_id": self.request_id, "tenant_id": self.tenant_id, "account": self.account,
            "query": self.query, "n_candidates": len(self.candidate_ids),
            "injected_ids": self.injected_ids, "tokens_used": self.tokens_used,
            "abstained": self.abstained, "stages": self.stages, "notes": self.notes,
        }


_TRACES: Dict[str, Trace] = {}


def get_trace(request_id) -> Optional[Trace]:
    """The `/trace/{id}` endpoint's backing lookup (api_contracts.md)."""
    return _TRACES.get(request_id)


def clear():
    _TRACES.clear()


def traced_retrieve(repo, *, query, account, request_id, user_id=None, clock=None,
                    token_budget=injection.TOKEN_BUDGET,
                    abstain_threshold=injection.ABSTAIN_THRESHOLD):
    """Retrieve + rank + inject, recording a full decision trace and writing the audit row.

    Returns (injected_ranked_items, Trace). Raises AuditWriteError if the audit write fails — the
    caller gets NO results in that case (fail closed, I9).
    """
    now = clock or (lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    t = Trace(request_id=request_id, tenant_id=repo.tenant_id, account=account, query=query)

    candidates = retrieval.candidates(repo, account)
    t.candidate_ids = [f.id for f in candidates]

    ranked = ranking.rank(query, account, candidates)
    for r in ranked:
        t.scores[r.fact.id] = {"score": round(r.score, 4), "lexical": round(r.lexical, 4),
                               "account": r.fact.account}

    # Re-derive the injection decision stage-by-stage so every drop has a recorded reason.
    grounded = [r for r in ranked
                if r.fact.account == account and r.lexical >= abstain_threshold]
    injected = injection.select(ranked, account, token_budget, abstain_threshold)
    injected_ids = {r.fact.id for r in injected}

    used, seen = 0, set()
    for r in ranked:
        mid = r.fact.id
        if mid in injected_ids:
            t.stages[mid] = "injected"
            used += injection.estimate_tokens(r.fact.text)
            seen.add((r.fact.account, r.fact.subject))
            continue
        if r.lexical < abstain_threshold:
            t.stages[mid] = "below_threshold"
        elif not grounded:
            t.stages[mid] = "not_grounded"          # nothing same-account cleared -> abstained
        elif (r.fact.account, r.fact.subject) in seen:
            t.stages[mid] = "deduped"
        elif r.fact.account != account:
            t.stages[mid] = "not_grounded"
        else:
            t.stages[mid] = "budget_dropped"

    t.injected_ids = [r.fact.id for r in injected]
    t.tokens_used = used
    t.abstained = not injected
    if t.abstained:
        t.notes.append("abstained: no same-account candidate cleared the relevance threshold")

    # ── audit FIRST, then return. No result without a log row (I9 / R5). ──
    try:
        repo.log_access(request_id=request_id, user_id=user_id,
                        returned_memory_ids=t.injected_ids, at=now())
    except Exception as e:                                   # noqa: BLE001 - fail closed on any error
        raise AuditWriteError(f"audit write failed; read refused for request {request_id}") from e

    _TRACES[request_id] = t
    return injected, t
