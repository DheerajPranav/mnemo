#!/usr/bin/env python3
"""
gate_g1_pii.py — [M2 / sprint S1] the PII admission gate (design/sprint_plan.md G1).

Claim under test: an admit carrying a phone/medical token stores NOTHING for that candidate, so the
sensitive memory can never be retrieved. On the fixed D3 set the PII exposure count goes 3 → 0.

Method: admit all 44 records through the real write path (mnemo.admission), then check that the
flagged memory (m009) is absent from every tenant's store — therefore unreachable by any query.

Exit 0 iff pii_exposure_count == 0 (baseline: 3). Computed, not narrated.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import _dataset
from mnemo.store import connect
from mnemo.repository import TenantRepository
from mnemo import admission


def main():
    memories = _dataset.load_memories()
    queries = _dataset.load_queries()

    conn = connect()
    repos = {}
    results = admission.admit_all(repos, memories, lambda t: TenantRepository(conn, t))
    conn.commit()

    blocked = [r for r in results if not r.stored and r.reason == "pii-blocked"]
    blocked_ids = {r.id for r in blocked}

    # every stored row, across every tenant
    all_stored_ids = set()
    for t, repo in repos.items():
        all_stored_ids |= {f.id for f in repo.all_facts()}

    # pii exposure: a stored memory flagged is_pii that a query could surface. Since blocked memories
    # are never stored, exposure is measured over what actually persisted.
    pii_ids_in_store = {m["id"] for m in memories if m["is_pii"]} & all_stored_ids
    pii_exposure_count = len(pii_ids_in_store)

    # the pii-probe query q07 must have no is_pii memory available among its tenant's current facts
    q07 = next(q for q in queries if q["id"] == "q07")
    t_repo = repos[q07["tenant"]]
    pii_flagged = {m["id"] for m in memories if m["is_pii"]}
    surfaceable = [f.id for f in t_repo.current_facts() if f.id in pii_flagged]

    print("=== GATE G1 · PII admission gate (M2 / S1) ===")
    print(f"records admitted:            {sum(1 for r in results if r.stored)}")
    print(f"records PII-blocked:         {len(blocked)}  (ids: {sorted(blocked_ids)})")
    print(f"is_pii memories in store:    {sorted(pii_ids_in_store) or 'none'}")
    print(f"pii surfaceable to q07:      {surfaceable or 'none'}")
    print(f"pii_exposure_count:          {pii_exposure_count}   (baseline: {_dataset.BASELINE['pii_exposure_count']})")

    # invariant I2 secondary check: the blocked result carries no raw text
    leaked_text = [r for r in blocked if "555-0142" in str(r.pii_entities)]

    ok = (pii_exposure_count == 0 and blocked_ids == {"m009"} and not surfaceable and not leaked_text)
    print(f"\nGATE G1: {'PASS ✅' if ok else 'FAIL ❌'}  "
          f"(criterion: pii_exposure_count == 0; blocked leaves no trace)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
