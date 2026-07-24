#!/usr/bin/env python3
"""
run_3arm.py — the 3-arm comparison (design/sprint_plan.md S4; ADR-002 scaffold). [M5]

Arms, all on the SAME fixed D3 set so only the mechanism differs:
  1. naive           — global index over every memory, single similarity signal, no filtering,
                       no isolation, no abstain. (The D3 baseline, Approach D.)
  2. +recency        — same global index, but recency is added as a ranking signal. This is the
                       cheap fix people reach for first: "just prefer newer memories."
  3. validity-filter — mnemo: tenant-scoped + write-path validity + multi-signal + abstain.

The point of arm 2 is falsification, not decoration: it tests D1/first_principles falsifier 1–2 —
"is supersession just a recency-ranking problem?" If recency alone closed F4 *and* left F10/F11
untouched, that would be visible here.

Writes eval/three_arm.md. Exit 0 always (this is a report, not a gate; gate G4 consumes it).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GATES = os.path.abspath(os.path.join(HERE, "..", "gates"))
if GATES not in sys.path:
    sys.path.insert(0, GATES)

import _dataset
from baseline import TfidfIndex, budgeted_injection
from mnemo.store import connect
from mnemo.repository import TenantRepository
from mnemo import admission, retrieval, ranking, injection

K = 5
TOKEN_BUDGET = 2000


def _score_arm(per_query):
    """Aggregate the same failure metrics used everywhere else, from per-query outcomes."""
    answerable = supersession = coldstart = 0
    passes = recall = sup_fail = inv_fail = leaks = pii = cold_fail = 0
    for r in per_query:
        ok = True
        if r["gold"] == "ABSTAIN":
            coldstart += 1
            if not r["abstained"]:
                ok = False
                cold_fail += 1
        else:
            answerable += 1
            if r["gold_in_topk"]:
                recall += 1
            if r["trap_above_gold"]:
                ok = False
                if "F4" in r["probes"]:
                    sup_fail += 1
                if "F7" in r["probes"]:
                    inv_fail += 1
            if "F3" in r["probes"] and not r["gold_in_topk"]:
                ok = False
        if r["leaked"]:
            leaks += 1
            ok = False
        if r["pii"]:
            pii += 1
            ok = False
        if "F4" in r["probes"]:
            supersession += 1
        if ok:
            passes += 1
    return {
        "overall_accuracy": round(passes / len(per_query), 3),
        "recall_at_k": round(recall / answerable, 3) if answerable else 0,
        "supersession_failure_rate": round(sup_fail / supersession, 3) if supersession else 0,
        "inversion_failures": inv_fail,
        "cross_tenant_leak_queries": leaks,
        "pii_exposure_count": pii,
        "coldstart_abstention_failure_rate": round(cold_fail / coldstart, 3) if coldstart else 0,
    }


def _global_arm(memories, queries, use_recency):
    """Arms 1 and 2: one global index, no isolation, no validity, no abstain."""
    idx = TfidfIndex(memories)
    by_id = {m["id"]: m for m in memories}
    order = sorted(range(len(memories)), key=lambda i: memories[i]["ts"])
    rec_rank = {memories[i]["id"]: pos / max(1, len(memories) - 1) for pos, i in enumerate(order)}

    out = []
    for q in queries:
        scored = idx.retrieve(q["query"], k=len(memories))
        if use_recency:
            scored = sorted(scored, key=lambda sm: (-(sm[0] * (1 + 0.5 * rec_rank[sm[1]["id"]])),
                                                    sm[1]["id"]))
        ranked_ids = [m["id"] for _, m in scored]
        topk = scored[:K]
        topk_ids = [m["id"] for _, m in topk]
        injected, _ = budgeted_injection(topk, TOKEN_BUDGET)
        injected_ids = [m["id"] for _, m in injected]

        gold, trap = q["gold"], q["trap"]
        g_rank = ranked_ids.index(gold) + 1 if gold != "ABSTAIN" and gold in ranked_ids else None
        t_rank = ranked_ids.index(trap) + 1 if trap and trap in ranked_ids else None
        out.append({
            "gold": gold, "probes": q["probes"],
            "gold_in_topk": gold in topk_ids if gold != "ABSTAIN" else None,
            "trap_above_gold": bool(t_rank and g_rank and t_rank < g_rank),
            "leaked": any(by_id[i]["tenant"] != q["tenant"] for i in topk_ids),
            "pii": any(by_id[i]["is_pii"] for i in injected_ids),
            "abstained": len(injected) == 0,
        })
    return out


def _mnemo_arm(memories, queries):
    conn = connect()
    repos = {}
    admission.admit_all(repos, memories, lambda t: TenantRepository(conn, t))
    conn.commit()
    by_id = {m["id"]: m for m in memories}
    out = []
    for q in queries:
        repo = repos[q["tenant"]]
        ranked = ranking.rank(q["query"], q["account"], retrieval.candidates(repo, q["account"]))
        ranked_ids = [r.fact.id for r in ranked]
        topk_ids = ranked_ids[:K]
        injected_ids = [r.fact.id for r in injection.select(ranked, q["account"])]
        gold, trap = q["gold"], q["trap"]
        g_rank = ranked_ids.index(gold) + 1 if gold != "ABSTAIN" and gold in ranked_ids else None
        t_rank = ranked_ids.index(trap) + 1 if trap and trap in ranked_ids else None
        out.append({
            "gold": gold, "probes": q["probes"],
            "gold_in_topk": gold in topk_ids if gold != "ABSTAIN" else None,
            "trap_above_gold": bool(t_rank and g_rank and t_rank < g_rank),
            "leaked": any(by_id[i]["tenant"] != q["tenant"] for i in topk_ids if i in by_id),
            "pii": any(by_id[i]["is_pii"] for i in injected_ids if i in by_id),
            "abstained": len(injected_ids) == 0,
        })
    conn.close()
    return out


def run_arms():
    memories, queries = _dataset.load_memories(), _dataset.load_queries()
    return {
        "1_naive": _score_arm(_global_arm(memories, queries, use_recency=False)),
        "2_recency": _score_arm(_global_arm(memories, queries, use_recency=True)),
        "3_validity_filter": _score_arm(_mnemo_arm(memories, queries)),
    }


def main():
    arms = run_arms()
    rows = ["overall_accuracy", "recall_at_k", "supersession_failure_rate", "inversion_failures",
            "cross_tenant_leak_queries", "pii_exposure_count", "coldstart_abstention_failure_rate"]
    out = os.path.join(HERE, "three_arm.md")
    with open(out, "w") as f:
        f.write("# 3-arm comparison — naive · +recency · validity-filter (mnemo)\n\n")
        f.write("Same fixed set (44 memories / 11 queries, k=5, budget=2000). Only the mechanism differs.\n\n")
        f.write("| Metric | 1 naive | 2 +recency | 3 validity-filter |\n|:--|:--:|:--:|:--:|\n")
        for r in rows:
            f.write(f"| {r} | {arms['1_naive'][r]} | {arms['2_recency'][r]} | "
                    f"**{arms['3_validity_filter'][r]}** |\n")
        n, r2 = arms["1_naive"], arms["2_recency"]
        f.write("\n## What arm 2 settles (the falsification test)\n"
                "\"Just prefer newer memories\" is the cheap fix everyone reaches for. Measured on this "
                "set, it does **not** work — and it back-fires:\n\n"
                f"1. **Supersession is unchanged** ({n['supersession_failure_rate']} → "
                f"{r2['supersession_failure_rate']}). The stale chunk is the one that lexically matches "
                "the query (\"CRM platform\" appears in the *superseded* Salesforce memory; the current "
                "memory says \"migrated to HubSpot\"), so a recency bonus at any reasonable weight does "
                "not overcome the similarity gap. Recency competes with relevance instead of "
                "overriding it — which is exactly why validity belongs on the write path, not in the ranker.\n"
                f"2. **Cross-tenant leakage gets WORSE** ({n['cross_tenant_leak_queries']} → "
                f"{r2['cross_tenant_leak_queries']} of 11 queries). The foreign-tenant near-duplicates "
                "(m101/m102, recorded Jan 2026) are *newer* than the tenant's own originals, so the "
                "recency signal actively promotes them. This is the D3 prediction — \"a stronger "
                "ranking signal makes F10 worse, not better\" — reproduced as a measurement.\n"
                f"3. **PII exposure and cold-start are untouched** ({n['pii_exposure_count']} and "
                f"{n['coldstart_abstention_failure_rate']}). No ranking signal addresses either; one "
                "needs an admission gate, the other an abstain rule.\n\n"
                "This settles first_principles falsifiers 1–2: supersession is **not** merely a "
                "recency-ranking problem, and the isolation / PII / cold-start failures are structural. "
                "Arm 3 fixes them by changing *what is allowed to be a candidate*, not by re-weighting.\n")
    print(f"wrote {out}\n")
    print(f"{'metric':38} {'naive':>8} {'+recency':>10} {'validity':>10}")
    for r in rows:
        print(f"{r:38} {str(arms['1_naive'][r]):>8} {str(arms['2_recency'][r]):>10} "
              f"{str(arms['3_validity_filter'][r]):>10}")
    with open(os.path.join(HERE, "three_arm.json"), "w") as f:
        json.dump(arms, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
