#!/usr/bin/env python3
"""
evaluate.py — run the naive baseline over the fixed evaluation set and MEASURE its failures.

Outputs (all written next to ../):
  ../baseline_results.csv   one row per query + an aggregate block
  ../error_examples.jsonl   one concrete failure per line, with the retrieved evidence
and prints an aggregate summary to stdout.

Reproducible: pure stdlib, fixed dataset, fixed k and budget. No randomness at eval time.
"""
import csv
import json
import os
import time

from baseline import TfidfIndex, budgeted_injection, estimate_tokens, load_jsonl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
EXP = os.path.abspath(os.path.join(HERE, ".."))

K = 5                    # top-k retrieved
TOKEN_BUDGET = 2000      # memory-injection budget (Deliverable 1 constraint: <=2000 of 16000)
ABSTAIN_THRESHOLD = 0.10 # a *reference* threshold; the naive baseline does NOT apply it (no abstain)
LATENCY_REPEATS = 200    # repeats per query to get a stable per-retrieval latency sample


def by_id(memories):
    return {m["id"]: m for m in memories}


def rank_of(ranked, mem_id):
    for i, (score, m) in enumerate(ranked, start=1):
        if m["id"] == mem_id:
            return i, score
    return None, None


def main():
    memories = load_jsonl(os.path.join(DATA, "memories.jsonl"))
    queries = load_jsonl(os.path.join(DATA, "queries.jsonl"))
    idx = TfidfIndex(memories)
    mid = by_id(memories)
    n = len(memories)

    rows = []
    errors = []
    latencies_ms = []

    # aggregate counters
    answerable = supersession = 0
    recall_hits = 0
    superseded_failures = 0
    inversion_failures = 0
    cross_tenant_queries = cross_tenant_leaks = 0
    pii_exposures = 0
    coldstart = coldstart_failures = 0
    passes = 0
    wasted_slots = total_slots = 0
    injected_token_counts = []

    for q in queries:
        ranked_full = idx.retrieve(q["query"], k=n)     # full ranking (for ranks)
        topk = ranked_full[:K]
        injected, used = budgeted_injection(topk, TOKEN_BUDGET)
        injected_ids = [m["id"] for _, m in injected]
        topk_ids = [m["id"] for _, m in topk]
        injected_token_counts.append(used)

        # latency sample (retrieval only)
        for _ in range(LATENCY_REPEATS):
            t0 = time.perf_counter()
            idx.retrieve(q["query"], k=K)
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        gold, trap = q["gold"], q["trap"]
        probes = q["probes"]
        failure_ids = []

        gold_rank, gold_score = (None, None) if gold == "ABSTAIN" else rank_of(ranked_full, gold)
        trap_rank, trap_score = (None, None) if not trap else rank_of(ranked_full, trap)
        gold_in_topk = gold in topk_ids if gold != "ABSTAIN" else None
        trap_above_gold = (trap is not None and gold != "ABSTAIN"
                           and trap_rank is not None and gold_rank is not None
                           and trap_rank < gold_rank)

        # cross-tenant leakage: any retrieved memory from a different tenant than the query
        leaked = [m["id"] for _, m in topk if mid[m["id"]]["tenant"] != q["tenant"]]
        # pii exposure: any injected memory flagged PII
        pii_hit = [m["id"] for _, m in injected if mid[m["id"]]["is_pii"]]
        abstained = len(injected) == 0

        # wasted-slot accounting (answerable queries): filler/duplicate in top-k
        if gold != "ABSTAIN":
            for _, m in topk:
                total_slots += 1
                if m["status"] == "filler":
                    wasted_slots += 1

        # ── condition-appropriate pass/fail + failure tagging ──
        cond = q["condition"]
        ok = True
        if gold == "ABSTAIN":
            coldstart += 1
            if not abstained:
                ok = False
                coldstart_failures += 1
                failure_ids.append("cold-start-no-abstain")
        else:
            answerable += 1
            if gold_in_topk:
                recall_hits += 1
            if trap_above_gold:
                ok = False
                if "F4" in probes:
                    superseded_failures += 1
                    failure_ids.append("F4")
                if "F7" in probes:
                    inversion_failures += 1
                    failure_ids.append("F7")
                if "F8" in probes and "F8" not in failure_ids:
                    failure_ids.append("F8")
            if "F3" in probes and not gold_in_topk:
                ok = False
                failure_ids.append("F3")

        if "F10" in probes or leaked:
            cross_tenant_queries += 1 if "F10" in probes else 0
            if leaked:
                cross_tenant_leaks += 1 if "F10" in probes else 0
                ok = False
                if "F10" not in failure_ids:
                    failure_ids.append("F10")
        if pii_hit:
            pii_exposures += 1
            ok = False
            if "F11" not in failure_ids:
                failure_ids.append("F11")

        if "F4" in probes:
            supersession += 1
        if ok:
            passes += 1

        rows.append({
            "query_id": q["id"], "condition": cond, "probes": "|".join(probes),
            "tenant": q["tenant"], "query": q["query"], "gold": gold, "trap": trap or "",
            "top1_id": topk_ids[0] if topk_ids else "",
            "top1_score": round(topk[0][0], 4) if topk else 0.0,
            "top1_tenant": mid[topk_ids[0]]["tenant"] if topk_ids else "",
            "gold_rank": gold_rank if gold_rank else "", "trap_rank": trap_rank if trap_rank else "",
            "gold_in_topk": gold_in_topk if gold != "ABSTAIN" else "",
            "trap_above_gold": trap_above_gold if trap else "",
            "cross_tenant_leak": "|".join(leaked), "pii_injected": "|".join(pii_hit),
            "injected_ids": "|".join(injected_ids), "injected_tokens": used,
            "abstained": abstained, "pass": ok, "failure_ids": "|".join(failure_ids),
        })

        if failure_ids:
            errors.append({
                "query_id": q["id"], "condition": cond, "query": q["query"],
                "failures": failure_ids, "gold": gold, "trap": trap,
                "retrieved_top3": [
                    {"rank": i + 1, "id": m["id"], "score": round(s, 4),
                     "tenant": mid[m["id"]]["tenant"], "is_pii": mid[m["id"]]["is_pii"],
                     "text": m["text"]}
                    for i, (s, m) in enumerate(topk[:3])
                ],
                "explanation": explain(failure_ids, q, mid, gold_rank, trap_rank),
            })

    latencies_ms.sort()
    p50 = latencies_ms[len(latencies_ms) // 2]
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]

    agg = {
        "n_memories": n,
        "n_queries": len(queries),
        "top_k": K,
        "token_budget": TOKEN_BUDGET,
        "overall_accuracy": round(passes / len(queries), 3),
        "recall_at_k": round(recall_hits / answerable, 3) if answerable else 0,
        "supersession_failure_rate": round(superseded_failures / supersession, 3) if supersession else 0,
        "inversion_failures": inversion_failures,
        "cross_tenant_leak_rate": round(cross_tenant_leaks / cross_tenant_queries, 3) if cross_tenant_queries else 0,
        "pii_exposure_count": pii_exposures,
        "coldstart_abstention_failure_rate": round(coldstart_failures / coldstart, 3) if coldstart else 0,
        "wasted_topk_slot_rate": round(wasted_slots / total_slots, 3) if total_slots else 0,
        "duplicate_or_filler_ratio": round(sum(1 for m in memories if m["status"] == "filler") / n, 3),
        "avg_injected_tokens": round(sum(injected_token_counts) / len(injected_token_counts), 1),
        "max_injected_tokens": max(injected_token_counts),
        "latency_p50_ms": round(p50, 4),
        "latency_p95_ms": round(p95, 4),
    }

    # write results.csv (per-query rows, then an aggregate block)
    csv_path = os.path.join(EXP, "baseline_results.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
        f.write("\n# AGGREGATE\n")
        for kk, vv in agg.items():
            f.write(f"# {kk},{vv}\n")

    with open(os.path.join(EXP, "error_examples.jsonl"), "w") as f:
        for e in errors:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # emit machine-readable aggregate for the report build
    with open(os.path.join(HERE, "metrics.json"), "w") as f:
        json.dump(agg, f, indent=2)

    print("=== NAIVE BASELINE — MEASURED RESULTS ===")
    for kk, vv in agg.items():
        print(f"{kk:38s} {vv}")
    print(f"\nwrote {csv_path}")
    print(f"wrote {os.path.join(EXP, 'error_examples.jsonl')} ({len(errors)} failure examples)")


def explain(failure_ids, q, mid, gold_rank, trap_rank):
    parts = []
    if "F4" in failure_ids:
        parts.append(f"stale fact {q['trap']} (rank {trap_rank}) outranks current fact "
                     f"{q['gold']} (rank {gold_rank}); similarity encodes surface match, not validity")
    if "F7" in failure_ids:
        parts.append(f"retrieved utterance {q['trap']} asserts the inverse of the account's "
                     f"actual position; a chunk is not a resolved fact")
    if "F10" in failure_ids:
        parts.append("a memory from a different tenant appears in top-k; no index-level isolation")
    if "F11" in failure_ids:
        parts.append("a PII memory was injected; nothing gated it at admission")
    if "F8" in failure_ids:
        parts.append("duplicate/filler chunks occupy top-k slots, crowding the informative memory")
    if "F3" in failure_ids:
        parts.append("the buried dealbreaker was not retrieved into the injected context")
    if "cold-start-no-abstain" in failure_ids:
        parts.append("no relevant memory exists, but the baseline injected chunks anyway "
                     "instead of abstaining (no similarity threshold)")
    return "; ".join(parts)


if __name__ == "__main__":
    main()
