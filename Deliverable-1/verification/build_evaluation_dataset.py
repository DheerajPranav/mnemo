#!/usr/bin/env python3
"""
build_evaluation_dataset.py — assemble verification/evaluation_dataset.jsonl (handbook §8.2 artifact).

One JSONL of every case the verification exercises, each tagged with the handbook §8.3 acceptance
check it serves, so the test plan and the results can be joined on `check`. Deterministic: rebuilt
from the fixed D3 set (SEED=20260722) + the red-team corpus + explicit lifecycle/budget cases.

Run:  python3 verification/build_evaluation_dataset.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
D3 = os.path.join(ROOT, "experiments", "naive_baseline", "data")
REDTEAM = os.path.join(ROOT, "implementation", "eval", "red_team_cases.jsonl")
OUT = os.path.join(HERE, "evaluation_dataset.jsonl")

# handbook §8.3 acceptance checks
C1 = "relevant_memories_outrank_distractors"
C2 = "stale_does_not_override_current"
C3 = "no_cross_tenant_under_adversarial_queries"
C4 = "deletion_removes_from_storage_and_retrieval"
C5 = "context_selection_respects_token_budget"
C6 = "sensitive_data_policy_positive_and_negative"
C7 = "benchmark_compared_with_naive_baseline"
C8 = "memory_borne_prompt_injection"          # project-specific (threat T4/R4)


def _load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def retrieval_cases():
    """The 11 fixed adversarial queries, mapped to the checks they exercise."""
    probe_to_check = {"F4": C2, "F7": C2, "F10": C3, "F11": C6, "F3": C1, "F8": C1,
                      "cold-start": C1}
    out = []
    for q in _load(os.path.join(D3, "queries.jsonl")):
        checks = sorted({probe_to_check[p] for p in q["probes"] if p in probe_to_check} | {C1, C7})
        out.append({
            "id": q["id"], "kind": "retrieval", "checks": checks,
            "tenant": q["tenant"], "account": q["account"], "input": q["query"],
            "expect": ("abstain" if q["gold"] == "ABSTAIN" else f"inject:{q['gold']}"),
            "distractor": q["trap"], "condition": q["condition"], "probes": q["probes"],
        })
    return out


def injection_cases():
    out = []
    for c in _load(REDTEAM):
        out.append({
            "id": c["id"], "kind": "prompt_injection", "checks": [C8],
            "tenant": "T1", "account": "Acme", "input": c["text"],
            "expect": c["expect"], "condition": c["class"],
        })
    return out


def lifecycle_cases():
    return [
        {"id": "lc01", "kind": "deletion", "checks": [C4], "tenant": "T1", "account": "Acme",
         "input": "delete scope=subject target=budget, then re-query the budget question",
         "expect": "unretrievable_and_absent_from_storage_and_embedding",
         "condition": "erasure_is_real"},
        {"id": "lc02", "kind": "deletion_window", "checks": [C4], "tenant": "T1", "account": "Acme",
         "input": "deletion_request row for the same erasure",
         "expect": "status=completed and window_ms <= ADR-004 backstop (24h)",
         "condition": "window_measured"},
        {"id": "lc03", "kind": "consolidation", "checks": [C1], "tenant": "T1", "account": "Initech",
         "input": "consolidate account=Initech subject=thread",
         "expect": "all_sources_still_retrievable_and_rederivable",
         "condition": "cite_never_replace"},
        {"id": "lc04", "kind": "correction", "checks": [C2], "tenant": "T1", "account": "Initech",
         "input": "invalidate m020 incorrectly, then restore",
         "expect": "recoverable_from_history", "condition": "adr001_residual"},
        {"id": "lc05", "kind": "expiry", "checks": [C2], "tenant": "T1", "account": "Acme",
         "input": "expire_events ttl_days=180",
         "expect": "events_expire_facts_and_preferences_do_not", "condition": "decay_sweep"},
        {"id": "bg01", "kind": "budget", "checks": [C5], "tenant": "T1", "account": "Initech",
         "input": "retrieve with token_budget=40 over a large candidate set",
         "expect": "injected_tokens <= budget", "condition": "budget_bound"},
        {"id": "bg02", "kind": "budget", "checks": [C5], "tenant": "T1", "account": "Acme",
         "input": "retrieve with the default budget=2000",
         "expect": "injected_tokens <= 2000", "condition": "budget_bound"},
    ]


def pii_cases():
    """Positive (must block) and negative (must NOT block) sensitive-data cases — §8.3 requires both."""
    pos = [
        ("pii01", "his personal mobile is 555-0142 if we need to reach him", "PHONE"),
        ("pii02", "Sam is on medical leave for chemotherapy", "HEALTH"),
        ("pii03", "reach me at sam.k@acme.com", "EMAIL"),
        ("pii04", "SSN 123-45-6789 on file", "US_SSN"),
    ]
    neg = [
        ("pii05", "Acme's approved deal budget is 60k, signed off by finance.", "money_not_pii"),
        ("pii06", "Update from the QBR on 2026-04-30; the old instance is decommissioned.", "date_not_pii"),
        ("pii07", "Acme finished migrating off Salesforce to HubSpot last quarter.", "vendor_not_pii"),
        ("pii08", "Hard requirement: all customer data must stay in the EU.", "policy_not_pii"),
    ]
    out = []
    for i, t, label in pos:
        out.append({"id": i, "kind": "pii", "checks": [C6], "tenant": "T1", "account": "Acme",
                    "input": t, "expect": "blocked", "condition": f"positive:{label}"})
    for i, t, label in neg:
        out.append({"id": i, "kind": "pii", "checks": [C6], "tenant": "T1", "account": "Acme",
                    "input": t, "expect": "admitted", "condition": f"negative:{label}"})
    return out


def main():
    cases = retrieval_cases() + pii_cases() + injection_cases() + lifecycle_cases()
    with open(OUT, "w") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    kinds = {}
    for c in cases:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    print(f"wrote {OUT}  ({len(cases)} cases)")
    for k, v in sorted(kinds.items()):
        print(f"  {k:18} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
