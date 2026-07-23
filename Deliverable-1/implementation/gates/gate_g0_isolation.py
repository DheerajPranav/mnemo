#!/usr/bin/env python3
"""
gate_g0_isolation.py — [M1 / sprint S0] the BLOCKING isolation gate (design/sprint_plan.md G0).

Claim under test: adding the tenant-isolation boundary — and holding the ranker CONSTANT at the
exact D3 baseline (baseline.TfidfIndex) — drops cross-tenant leakage to zero across all 11 queries.

Method: for each query, build the baseline TF-IDF index over ONLY the querying tenant's rows
(fetched through TenantRepository, invariant I1), take top-k, and count any foreign-tenant row.
Because foreign rows were never candidates, the ranker cannot leak them. This isolates the
isolation variable: same ranker as D3, only the candidate scope changed.

Exit 0 iff cross-tenant leak = 0 on every query (baseline: 7/11). Computed, not narrated.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import _dataset
from mnemo.store import connect
from baseline import TfidfIndex   # the EXACT D3 ranker, held constant

K = 5


def main():
    memories = _dataset.load_memories()
    queries = _dataset.load_queries()

    conn = connect()
    repos = _dataset.raw_load_into_store(conn, memories)

    leaked_queries = 0
    f10_probed = f10_leaks = 0
    details = []

    for q in queries:
        repo = repos.get(q["tenant"])
        # candidate set = ONLY this tenant's rows (invariant I1). Foreign rows are unreachable.
        candidates = [
            {"id": f.id, "text": f.text, "tenant": f.tenant_id} for f in repo.all_facts()
        ]
        idx = TfidfIndex(candidates)
        topk = idx.retrieve(q["query"], k=K)
        foreign = [m["id"] for _, m in topk if m["tenant"] != q["tenant"]]
        if foreign:
            leaked_queries += 1
        if "F10" in q["probes"]:
            f10_probed += 1
            if foreign:
                f10_leaks += 1
        details.append((q["id"], q["tenant"], repo.count(), len(foreign)))

    leak_rate = (f10_leaks / f10_probed) if f10_probed else 0.0

    print("=== GATE G0 · tenant isolation (M1 / S0) — BLOCKING ===")
    print(f"{'query':6} {'tenant':7} {'candidates':10} {'foreign_in_topk':15}")
    for qid, tenant, ncand, nf in details:
        print(f"{qid:6} {tenant:7} {ncand:<10} {nf:<15}")
    print("-" * 44)
    print(f"cross_tenant_leak (all queries):  {leaked_queries}/{len(queries)}   "
          f"(baseline: {_dataset.BASELINE['cross_tenant_leak_queries']}/11)")
    print(f"cross_tenant_leak_rate (F10-probed): {leak_rate:.3f}   "
          f"(baseline: {_dataset.BASELINE['cross_tenant_leak_rate']:.3f})")

    ok = (leaked_queries == 0)
    print(f"\nGATE G0: {'PASS ✅' if ok else 'FAIL ❌'}  "
          f"(criterion: 0 foreign-tenant rows on every query)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
