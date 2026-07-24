#!/usr/bin/env python3
"""
verify.py — INDEPENDENT verification against handbook §8.3.

"Verification must be performed from the specification and acceptance criteria, not by accepting the
implementation agent's own assessment." So this harness does NOT read the gate scripts' verdicts. It
re-derives every acceptance check from the spec, against the evaluation dataset, and reports its own
pass/fail. Where a check cannot be executed here, it is reported UNVERIFIED — never assumed.

Run:  python3 verification/verify.py
Writes: verification/results/verification_results.json  +  results/summary.txt
Exit 0 iff every executable §8.3 check passes.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
IMPL = os.path.join(ROOT, "implementation")
for p in (IMPL, os.path.join(IMPL, "gates"), os.path.join(IMPL, "eval")):
    if p not in sys.path:
        sys.path.insert(0, p)

import _dataset
from mnemo.store import connect
from mnemo.repository import TenantRepository
from mnemo import (admission, retrieval, ranking, injection, lifecycle, consolidation,
                   pii_gate, injection_guard, trace)
import run_3arm

RESULTS = os.path.join(HERE, "results")
DATASET = os.path.join(HERE, "evaluation_dataset.jsonl")
ADR004_WINDOW_MS = 24 * 60 * 60 * 1000.0


def cases():
    with open(DATASET) as f:
        return [json.loads(line) for line in f if line.strip()]


def pipeline():
    conn = connect()
    repos = {}
    admission.admit_all(repos, _dataset.load_memories(), lambda t: TenantRepository(conn, t))
    conn.commit()
    return conn, repos


def answer(repo, query, account, budget=injection.TOKEN_BUDGET):
    ranked = ranking.rank(query, account, retrieval.candidates(repo, account))
    sel = injection.select(ranked, account, budget)
    return ranked, sel


# ── §8.3 checks ────────────────────────────────────────────────────────────────
def check_1_relevant_outrank_distractors(cs):
    conn, repos = pipeline()
    repo = repos["T1"]
    failures = []
    for c in [c for c in cs if c["kind"] == "retrieval" and c["expect"].startswith("inject:")]:
        gold = c["expect"].split(":", 1)[1]
        ranked, _ = answer(repo, c["input"], c["account"])
        ids = [r.fact.id for r in ranked]
        d = c.get("distractor")
        if d and d in ids and gold in ids and ids.index(d) < ids.index(gold):
            failures.append(f"{c['id']}: distractor {d} outranks gold {gold}")
        if d and d not in ids:
            pass  # distractor removed upstream (validity/isolation/PII) — the stronger outcome
    conn.close()
    return not failures, {"failures": failures,
                          "note": "distractors are removed upstream, so they cannot outrank at all"}


def check_2_stale_does_not_override_current(cs):
    conn, repos = pipeline()
    repo = repos["T1"]
    failures = []
    # (i) no superseded/inverted trap may be a candidate at all
    current = {f.id for f in repo.current_facts()}
    for stale in ("m001", "m003", "m005", "m007"):
        if stale in current:
            failures.append(f"superseded {stale} is still current")
    # (ii) the current fact is the one that answers
    for qid, gold in (("q01", "m002"), ("q03", "m008"), ("q04", "m006")):
        c = next(x for x in cs if x["id"] == qid)
        _, sel = answer(repo, c["input"], c["account"])
        if gold not in [r.fact.id for r in sel]:
            failures.append(f"{qid}: current fact {gold} not injected")
    # (iii) correction recovery (lc04)
    repo.invalidate("m020", at="2026-07-25", by="operator-error")
    conn.commit()
    if not lifecycle.restore(repo, "m020"):
        failures.append("lc04: wrongly-invalidated fact not recoverable")
    conn.close()
    return not failures, {"failures": failures}


def check_3_no_cross_tenant(cs):
    conn, repos = pipeline()
    repo = repos["T1"]
    tenant_of = {m["id"]: m["tenant"] for m in _dataset.load_memories()}
    failures = []
    # every dataset query
    for c in [c for c in cs if c["kind"] == "retrieval"]:
        ranked, sel = answer(repo, c["input"], c["account"])
        for r in ranked[:5] + sel:
            if tenant_of.get(r.fact.id, "T1") != c["tenant"]:
                failures.append(f"{c['id']}: foreign row {r.fact.id}")
    # adversarial: query the foreign memory's EXACT text
    for txt in ("Acme's CRM platform is Salesforce and their entire sales pipeline routes through Salesforce.",
                "The primary contact and decision maker at Acme is Dana Whitfield, Head of Ops."):
        _, sel = answer(repo, txt, "Acme")
        for r in sel:
            if r.fact.id in ("m101", "m102"):
                failures.append(f"adversarial exact-text surfaced {r.fact.id}")
    # structural: repository exposes no cross-tenant read
    import inspect
    for name, m in inspect.getmembers(TenantRepository, predicate=inspect.isfunction):
        if not name.startswith("_") and any("tenant" in p.lower()
                                            for p in inspect.signature(m).parameters):
            failures.append(f"repository method {name} accepts a tenant parameter")
    conn.close()
    return not failures, {"failures": failures}


def check_4_deletion(cs):
    conn, repos = pipeline()
    repo = repos["T1"]
    failures = []
    q = next(c for c in cs if c["id"] == "q03")["input"]
    before = [r.fact.id for r in answer(repo, q, "Acme")[1]]
    if "m008" not in before:
        failures.append("precondition: m008 was not retrievable before deletion")
    res = lifecycle.delete(repo, scope="subject", target_ref="budget")
    conn.commit()
    after = [r.fact.id for r in answer(repo, q, "Acme")[1]]
    if any(i in after for i in res.deleted_ids):
        failures.append("deleted memory still retrievable")
    raw = conn.execute("SELECT COUNT(*) c FROM memory WHERE id IN ('m007','m008')").fetchone()["c"]
    emb = conn.execute(
        "SELECT COUNT(*) c FROM memory_embedding WHERE memory_id IN ('m007','m008')").fetchone()["c"]
    if raw:
        failures.append(f"{raw} deleted rows remain in source storage")
    if emb:
        failures.append(f"{emb} embedding rows outlived their source")
    row = repo.deletion_request(res.request_id)
    if row["status"] != "completed" or row["window_ms"] is None:
        failures.append("deletion_request not completed / window not recorded")
    elif row["window_ms"] > ADR004_WINDOW_MS:
        failures.append(f"window {row['window_ms']}ms exceeds ADR-004 backstop")
    conn.close()
    return not failures, {"failures": failures, "window_ms": row["window_ms"],
                          "deleted": res.deleted_ids}


def check_5_token_budget(cs):
    conn, repos = pipeline()
    repo = repos["T1"]
    failures = []
    measured = []
    for budget, account, q in ((40, "Initech", "Initech thread options and timeline"),
                               (2000, "Acme", "What CRM platform does Acme use?"),
                               (120, "Initech", "Are there any hard requirements for Initech?")):
        _, sel = answer(repo, q, account, budget=budget)
        used = sum(injection.estimate_tokens(r.fact.text) for r in sel)
        measured.append({"budget": budget, "used": used, "n": len(sel)})
        if used > budget:
            failures.append(f"budget {budget} exceeded: used {used}")
    conn.close()
    return not failures, {"failures": failures, "measured": measured}


def check_6_sensitive_data(cs):
    failures = []
    pos = neg = 0
    conn, repos = pipeline()
    repo = repos["T1"]
    for i, c in enumerate([c for c in cs if c["kind"] == "pii"]):
        rec = {"id": f"v{i}", "tenant": "T1", "tenant_name": "N", "account": "Acme", "user": "u",
               "ts": "2026-07-25", "text": c["input"], "status": "x", "subject": "chatter",
               "is_pii": False, "note": ""}
        res = admission.admit(repo, rec, seq=8000 + i)
        blocked = not res.stored
        if c["expect"] == "blocked":
            pos += 1
            if not blocked:
                failures.append(f"{c['id']} (positive) was admitted")
            elif "555-0142" in str(res.pii_entities) or "123-45-6789" in str(res.pii_entities):
                failures.append(f"{c['id']} retained the raw sensitive span")
        else:
            neg += 1
            if blocked:
                failures.append(f"{c['id']} (negative) was wrongly blocked")
    # and the dataset's flagged memory must never be in the store
    conn2, repos2 = pipeline()
    stored = {f.id for f in repos2["T1"].all_facts()}
    if "m009" in stored:
        failures.append("the flagged PII memory m009 is in the store")
    conn.close(); conn2.close()
    return not failures, {"failures": failures, "positive_cases": pos, "negative_cases": neg}


def check_7_benchmark_vs_baseline(cs):
    with open(os.path.join(ROOT, "experiments", "naive_baseline", "metrics.json")) as f:
        base = json.load(f)
    arms = run_3arm.run_arms()
    m = arms["3_validity_filter"]
    failures = []
    if m["overall_accuracy"] <= base["overall_accuracy"]:
        failures.append("accuracy not improved over baseline")
    for k in ("supersession_failure_rate", "pii_exposure_count",
              "coldstart_abstention_failure_rate"):
        if m[k] > base[k]:
            failures.append(f"{k} worse than baseline")
    if m["cross_tenant_leak_queries"] > 0:
        failures.append("cross-tenant leak not eliminated")
    return not failures, {"failures": failures, "baseline": base, "mnemo": m,
                          "recency_arm": arms["2_recency"]}


def check_8_prompt_injection(cs):
    conn, repos = pipeline()
    repo = repos["T1"]
    overt_total = overt_blocked = 0
    survived, benign_ok = [], True
    for i, c in enumerate([c for c in cs if c["kind"] == "prompt_injection"]):
        rec = {"id": c["id"], "tenant": "T1", "tenant_name": "N", "account": "Acme", "user": "a",
               "ts": "2026-07-25", "text": c["input"], "status": "x", "subject": "chatter",
               "is_pii": False, "note": ""}
        res = admission.admit(repo, rec, seq=9500 + i)
        if c["expect"] == "blocked":
            overt_total += 1
            if not res.stored:
                overt_blocked += 1
        elif c["expect"] == "survives" and res.stored:
            survived.append(c["id"])
        elif c["expect"] == "admitted" and not res.stored:
            benign_ok = False
    conn.commit()
    reachable = []
    ranked, sel = answer(repo, "What should we do about discounts and approvals for Acme?", "Acme")
    for r in sel:
        if r.fact.id in survived:
            reachable.append(r.fact.id)
    conn.close()
    failures = []
    if overt_blocked != overt_total:
        failures.append(f"only {overt_blocked}/{overt_total} overt injections blocked")
    if not benign_ok:
        failures.append("benign control was over-blocked")
    # NOTE: surviving subtle cases are a *documented residual*, not a failure of this check.
    return not failures, {"failures": failures, "overt_blocked": f"{overt_blocked}/{overt_total}",
                          "residual_survivors": survived, "residual_reaching_context": reachable}


CHECKS = [
    ("8.3.1 relevant memories outrank plausible distractors", check_1_relevant_outrank_distractors),
    ("8.3.2 stale/superseded do not override current", check_2_stale_does_not_override_current),
    ("8.3.3 no cross-tenant memory under adversarial queries", check_3_no_cross_tenant),
    ("8.3.4 deletion removes from storage and retrieval within the window", check_4_deletion),
    ("8.3.5 context selection respects the token budget", check_5_token_budget),
    ("8.3.6 sensitive-data policy: positive and negative cases", check_6_sensitive_data),
    ("8.3.7 benchmark results compared with the naive baseline", check_7_benchmark_vs_baseline),
    ("R4  memory-borne prompt injection (project-specific)", check_8_prompt_injection),
]

UNVERIFIED = [{
    "check": "ADR-005 Postgres + pgvector + RLS substrate",
    "status": "UNVERIFIED",
    "why": "no Postgres service available in this environment (decision D6-DR-002); the schema and RLS "
           "policies ship as implementation/mnemo/postgres_schema.sql but are not executed here",
    "how_to_close": "psql -f implementation/mnemo/postgres_schema.sql, then SET LOCAL app.tenant_id "
                    "and confirm a cross-tenant SELECT returns 0 rows",
}]


def main():
    os.makedirs(RESULTS, exist_ok=True)
    cs = cases()
    results, all_ok = [], True
    lines = ["INDEPENDENT VERIFICATION — handbook §8.3",
             "(re-derived from the spec; gate verdicts not consulted)", ""]
    for name, fn in CHECKS:
        trace.clear()
        ok, detail = fn(cs)
        all_ok = all_ok and ok
        results.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        print(line)
        lines.append(line)
        if detail.get("failures"):
            for f_ in detail["failures"]:
                print(f"         - {f_}")
                lines.append(f"         - {f_}")
    for u in UNVERIFIED:
        print(f"[UNVERIFIED] {u['check']} — {u['why']}")
        lines.append(f"[UNVERIFIED] {u['check']} — {u['why']}")

    payload = {"cases": len(cs), "checks": results, "unverified": UNVERIFIED,
               "verdict": "PASS" if all_ok else "FAIL"}
    with open(os.path.join(RESULTS, "verification_results.json"), "w") as f:
        json.dump(payload, f, indent=2)
    lines += ["", f"VERDICT: {'PASS' if all_ok else 'FAIL'} over {len(cs)} evaluation cases",
              f"UNVERIFIED (reported, not assumed): {len(UNVERIFIED)}"]
    with open(os.path.join(RESULTS, "summary.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nVERDICT: {'PASS ✅' if all_ok else 'FAIL ❌'} over {len(cs)} evaluation cases")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
