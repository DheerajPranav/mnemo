#!/usr/bin/env python3
"""
gate_g3_lifecycle.py — [M4 / sprint S3] the lifecycle gate (design/sprint_plan.md G3). HIGH-RISK.

Three checks, exactly as the sprint plan specifies:
  (a) consolidation keeps every source retrievable and re-derivable            (F5/F6, invariant I8)
  (b) delete-then-requery is unretrievable within the window; window_ms recorded (F9, invariant I7)
  (c) an incorrectly invalidated fact is recoverable from history               (ADR-001 residual)

Runs against a throwaway in-memory store built from the fixed D3 dataset (never a file-backed DB).
Exit 0 iff all three pass. Computed, not narrated.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import _dataset
from mnemo.store import connect
from mnemo.repository import TenantRepository
from mnemo import admission, retrieval, ranking, injection, lifecycle, consolidation

ADR004_WINDOW_MS = 24 * 60 * 60 * 1000.0   # ADR-004 backstop: deletion completes within 24h


def build():
    conn = connect()                        # :memory: — safety rule from M4-pre-highrisk.md
    repos = {}
    admission.admit_all(repos, _dataset.load_memories(), lambda t: TenantRepository(conn, t))
    conn.commit()
    return conn, repos["T1"]


def answers(repo, query, account):
    ranked = ranking.rank(query, account, retrieval.candidates(repo, account))
    return [r.fact.id for r in injection.select(ranked, account)]


def check_a_consolidation():
    """Consolidation cites; sources stay retrievable and the rollup is re-derivable."""
    conn, repo = build()
    before = {f.id for f in repo.current_facts()}
    # roll up the Initech conversation-thread turns (the long, low-signal 'thread' subject)
    rollup_id, source_ids = consolidation.consolidate(
        repo, account="Initech", subject="thread", rollup_id="r001",
        summary_text="Rollup: Initech thread covered intros, SSO options, timeline and pricing.",
        at="2026-07-25", seq=9000)
    conn.commit()

    sources_still_current = [sid for sid in source_ids
                             if any(f.id == sid for f in repo.current_facts())]
    rederived = [f.id for f in consolidation.rederive(repo, rollup_id)]
    after = {f.id for f in repo.current_facts()}

    ok = (len(source_ids) > 0
          and len(sources_still_current) == len(source_ids)      # nothing invalidated
          and sorted(rederived) == sorted(source_ids)            # fully re-derivable
          and before.issubset(after))                            # purely additive
    print(f"(a) consolidation: {len(source_ids)} sources cited · still retrievable "
          f"{len(sources_still_current)}/{len(source_ids)} · re-derivable "
          f"{len(rederived)}/{len(source_ids)} · additive={before.issubset(after)}  -> "
          f"{'PASS' if ok else 'FAIL'}")
    return ok


def check_b_deletion():
    """Delete-then-requery returns nothing; embeddings cascade; window measured and within ADR-004."""
    conn, repo = build()
    q = "What is Acme's approved budget for the deal?"
    before_ids = answers(repo, q, "Acme")
    emb_before = repo.embedding_count_for(["m008"])

    res = lifecycle.delete(repo, scope="subject", target_ref="budget")
    conn.commit()

    after_ids = answers(repo, q, "Acme")
    row = repo.deletion_request(res.request_id)
    still_in_store = [f.id for f in repo.all_facts() if f.id in res.deleted_ids]

    ok = ("m008" in before_ids                       # it WAS retrievable
          and not any(i in after_ids for i in res.deleted_ids)   # now unretrievable
          and not still_in_store                     # gone from source storage
          and res.embeddings_remaining == 0          # projection cascaded
          and emb_before > 0                         # the projection existed to begin with
          and row["status"] == "completed" and row["completed_at"] is not None
          and row["window_ms"] is not None and row["window_ms"] <= ADR004_WINDOW_MS)
    print(f"(b) deletion: retrievable before={before_ids or '-'} · deleted={res.deleted_ids} · "
          f"retrievable after={after_ids or 'none'} · embeddings_remaining={res.embeddings_remaining} "
          f"· window_ms={res.window_ms:.4f} (<= ADR-004 {ADR004_WINDOW_MS:.0f}) · "
          f"status={row['status']}  -> {'PASS' if ok else 'FAIL'}")
    return ok


def check_c_recover_wrong_invalidation():
    """A fact invalidated INCORRECTLY is recoverable from history."""
    conn, repo = build()
    victim = "m020"                                   # Initech data-residency dealbreaker
    assert any(f.id == victim for f in repo.current_facts())
    repo.invalidate(victim, at="2026-07-25", by="operator-error")
    conn.commit()
    gone = not any(f.id == victim for f in repo.current_facts())
    in_history = any(f.id == victim for f in repo.invalidated_facts())

    recovered = lifecycle.restore(repo, victim)
    conn.commit()
    retrievable_again = victim in answers(
        repo, "Are there any hard requirements or dealbreakers for Initech?", "Initech")

    ok = gone and in_history and recovered and retrievable_again
    print(f"(c) correction recovery: invalidated={gone} · present_in_history={in_history} · "
          f"restored={recovered} · retrievable_again={retrievable_again}  -> "
          f"{'PASS' if ok else 'FAIL'}")
    return ok


def main():
    print("=== GATE G3 · lifecycle: consolidate / delete / correct (M4 / S3) — HIGH-RISK ===")
    a = check_a_consolidation()
    b = check_b_deletion()
    c = check_c_recover_wrong_invalidation()
    ok = a and b and c
    print(f"\nGATE G3: {'PASS ✅' if ok else 'FAIL ❌'}  (criterion: a AND b AND c)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
