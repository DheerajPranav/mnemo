#!/usr/bin/env python3
"""
gate_g2_baseline.py — [M3 / sprint S2] the read-path gate: BEAT the D3 baseline (sprint_plan G2).

Runs the full mnemo pipeline (admit -> current_facts -> rank -> inject) over the SAME fixed D3 set
and computes the SAME failure metrics as experiments/naive_baseline/evaluate.py, so every number is
a like-for-like comparison. This is the design's core claim, proven or falsified — computed, not narrated.

Pass criterion (design/sprint_plan.md G2, tightened to the read path's whole remit):
  supersession_failure_rate < 0.80  AND  cross_tenant_leak == 0  AND  inversion_failures == 0
  AND  pii_exposure_count == 0  AND  coldstart_abstention_failure_rate == 0  AND  accuracy > baseline.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import _dataset
from mnemo.store import connect
from mnemo.repository import TenantRepository
from mnemo import admission, retrieval, ranking, injection

K = 5


def rank_of(ranked, mem_id):
    for i, r in enumerate(ranked, start=1):
        if r.fact.id == mem_id:
            return i
    return None


def main():
    memories = _dataset.load_memories()
    queries = _dataset.load_queries()
    by_pii = {m["id"] for m in memories if m["is_pii"]}

    conn = connect()
    repos = {}
    admission.admit_all(repos, memories, lambda t: TenantRepository(conn, t))
    conn.commit()

    answerable = supersession = coldstart = 0
    passes = recall_hits = 0
    superseded_failures = inversion_failures = 0
    cross_tenant_leaks_all = pii_exposures = coldstart_failures = 0
    rows = []

    for q in queries:
        repo = repos[q["tenant"]]
        facts = retrieval.candidates(repo, q["account"])
        ranked = ranking.rank(q["query"], q["account"], facts)
        topk = ranked[:K]
        topk_ids = [r.fact.id for r in topk]
        injected = injection.select(ranked, q["account"])
        injected_ids = [r.fact.id for r in injected]
        abstained = len(injected) == 0

        gold, trap, probes = q["gold"], q["trap"], q["probes"]
        gold_rank = None if gold == "ABSTAIN" else rank_of(ranked, gold)
        trap_rank = rank_of(ranked, trap) if trap else None
        gold_in_topk = (gold in topk_ids) if gold != "ABSTAIN" else None
        trap_above_gold = (trap_rank is not None and gold_rank is not None and trap_rank < gold_rank)

        leaked = [i for i in topk_ids if repo_tenant(memories, i) != q["tenant"]]
        pii_hit = [i for i in injected_ids if i in by_pii]

        ok = True
        if gold == "ABSTAIN":
            coldstart += 1
            if not abstained:
                ok = False
                coldstart_failures += 1
        else:
            answerable += 1
            if gold_in_topk:
                recall_hits += 1
            if trap_above_gold:
                ok = False
                if "F4" in probes:
                    superseded_failures += 1
                if "F7" in probes:
                    inversion_failures += 1
            if "F3" in probes and not gold_in_topk:
                ok = False
        if leaked:
            cross_tenant_leaks_all += 1
            ok = False
        if pii_hit:
            pii_exposures += 1
            ok = False
        if "F4" in probes:
            supersession += 1
        if ok:
            passes += 1

        rows.append((q["id"], q["condition"][:22], gold, trap or "-",
                     topk_ids[0] if topk_ids else "-", gold_rank or "-",
                     "abstain" if abstained else injected_ids[0] if injected_ids else "-",
                     "PASS" if ok else "FAIL"))

    agg = {
        "overall_accuracy": round(passes / len(queries), 3),
        "recall_at_k": round(recall_hits / answerable, 3) if answerable else 0,
        "supersession_failure_rate": round(superseded_failures / supersession, 3) if supersession else 0,
        "inversion_failures": inversion_failures,
        "cross_tenant_leak_queries": cross_tenant_leaks_all,
        "pii_exposure_count": pii_exposures,
        "coldstart_abstention_failure_rate": round(coldstart_failures / coldstart, 3) if coldstart else 0,
    }

    print("=== GATE G2 · read path — beat the D3 baseline (M3 / S2) ===")
    print(f"{'q':4} {'condition':23} {'gold':7} {'trap':6} {'top1':7} {'g_rk':5} {'injected':9} {'res':4}")
    for r in rows:
        print(f"{r[0]:4} {r[1]:23} {r[2]:7} {r[3]:6} {r[4]:7} {str(r[5]):5} {r[6]:9} {r[7]:4}")
    print("-" * 72)
    b = _dataset.BASELINE
    print(f"{'metric':38} {'mnemo':>8} {'baseline':>10}")
    print(f"{'overall_accuracy':38} {agg['overall_accuracy']:>8} {b['overall_accuracy']:>10}")
    print(f"{'supersession_failure_rate':38} {agg['supersession_failure_rate']:>8} {b['supersession_failure_rate']:>10}")
    print(f"{'inversion_failures':38} {agg['inversion_failures']:>8} {'1':>10}")
    print(f"{'cross_tenant_leak_queries':38} {agg['cross_tenant_leak_queries']:>8} {b['cross_tenant_leak_queries']:>10}")
    print(f"{'pii_exposure_count':38} {agg['pii_exposure_count']:>8} {b['pii_exposure_count']:>10}")
    print(f"{'coldstart_abstention_failure_rate':38} {agg['coldstart_abstention_failure_rate']:>8} {b['coldstart_abstention_failure_rate']:>10}")

    ok = (agg["supersession_failure_rate"] < 0.80 and agg["cross_tenant_leak_queries"] == 0
          and agg["inversion_failures"] == 0 and agg["pii_exposure_count"] == 0
          and agg["coldstart_abstention_failure_rate"] == 0
          and agg["overall_accuracy"] > b["overall_accuracy"])
    print(f"\nGATE G2: {'PASS ✅' if ok else 'FAIL ❌'}")
    return 0 if ok else 1


def repo_tenant(memories, mem_id):
    for m in memories:
        if m["id"] == mem_id:
            return m["tenant"]
    return None


if __name__ == "__main__":
    sys.exit(main())
