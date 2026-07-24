"""
lifecycle.py — correction, deletion, expiry. [M4]

Invariant **I7 (deletion is real)**: a deletion removes the fact from source storage AND every
retrieval path in one transaction; the embedding projection cascades (ADR-005). The `deletion_request`
row records requested_at/completed_at so the F9 consistency window is **measured, not hoped for**.

Correction path (ADR-001 residual): invalidating a fact must never lose it. `correct()` invalidates
and re-admits; `restore()` recovers a fact that was invalidated *incorrectly* — the history in
`memory` (invalidated_at/invalidated_by) is what makes that possible.

Expiry: v1 expires **events** past a TTL (a call note stops being current), and deliberately does NOT
auto-expire facts/preferences — those end by supersession (ADR-001), not by clock. Expiring a fact on
a timer would silently drop a still-true fact, which is F5 wearing a different hat.
"""
import time
from dataclasses import dataclass, field
from typing import List

from . import admission


@dataclass
class DeletionResult:
    request_id: int
    deleted_ids: List[str] = field(default_factory=list)
    window_ms: float = 0.0
    embeddings_remaining: int = 0


def delete(repo, *, scope, target_ref, clock=None):
    """Hard-delete every fact this tenant holds matching (scope, target_ref), measuring the window.

    scope ∈ {account, subject, actor}. The deletion_request is opened BEFORE and completed AFTER, so
    `window_ms` is the real elapsed time of the erasure, not an assertion about it.
    """
    now = clock or (lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    t0 = time.perf_counter()
    request_id = repo.open_deletion_request(scope=scope, target_ref=target_ref, at=now())

    targets = repo.facts_matching(scope=scope, target_ref=target_ref)
    ids = [f.id for f in targets]
    for mid in ids:
        repo.delete(mid)                      # cascades memory_embedding (I7)

    window_ms = (time.perf_counter() - t0) * 1000.0
    repo.complete_deletion_request(request_id, at=now(), window_ms=window_ms)
    repo.commit() if hasattr(repo, "commit") else None

    return DeletionResult(
        request_id=request_id, deleted_ids=ids, window_ms=window_ms,
        embeddings_remaining=repo.embedding_count_for(ids),
    )


def correct(repo, *, wrong_id, corrected_record, seq, at):
    """Correct a fact: invalidate the wrong one, admit the corrected one. The wrong fact stays in
    history (recoverable via `restore`) — correction is not deletion."""
    repo.invalidate(wrong_id, at=at, by=corrected_record["id"])
    return admission.admit(repo, corrected_record, seq)


def restore(repo, memory_id):
    """Recover a fact that was invalidated incorrectly (the ADR-001 residual). Returns True if the
    fact is current again."""
    repo.restore(memory_id)
    return any(f.id == memory_id for f in repo.current_facts())


def expire_events(repo, *, now_date, ttl_days, at=None):
    """Expiry sweep: invalidate `event` memories older than ttl_days. Facts/preferences are NOT
    expired on a timer — they end by supersession. Returns the ids expired."""
    at = at or now_date
    cutoff = _days_before(now_date, ttl_days)
    expired = []
    for f in repo.current_facts():
        if f.mem_type == "event" and f.recorded_at < cutoff:
            repo.invalidate(f.id, at=at, by="expiry-sweep")
            expired.append(f.id)
    return expired


def _days_before(date_str, days):
    """Date arithmetic on ISO 'YYYY-MM-DD' without pulling a dependency."""
    y, m, d = (int(x) for x in date_str[:10].split("-"))
    # days since epoch via a simple civil-date algorithm, then back
    def to_ord(y, m, d):
        a = (14 - m) // 12
        yy = y + 4800 - a
        mm = m + 12 * a - 3
        return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
    def from_ord(n):
        a = n + 32044
        b = (4 * a + 3) // 146097
        c = a - 146097 * b // 4
        dd = (4 * c + 3) // 1461
        e = c - 1461 * dd // 4
        mm = (5 * e + 2) // 153
        day = e - (153 * mm + 2) // 5 + 1
        month = mm + 3 - 12 * (mm // 10)
        year = 100 * b + dd - 4800 + mm // 10
        return f"{year:04d}-{month:02d}-{day:02d}"
    return from_ord(to_ord(y, m, d) - days)
