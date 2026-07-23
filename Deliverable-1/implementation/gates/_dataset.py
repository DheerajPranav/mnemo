"""
_dataset.py — shared loader so every gate runs against the SAME fixed dataset the D3 baseline was
measured on (experiments/naive_baseline/data, SEED=20260722). This is what makes "beat the baseline"
a real, computed claim rather than a narrated one.

Also puts the baseline dir on sys.path so gates can import the *exact* baseline ranker
(baseline.TfidfIndex) and hold ranking constant when isolating a single variable (e.g. G0).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMPL = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(IMPL, ".."))                       # Deliverable-1/
BASELINE_DIR = os.path.join(ROOT, "experiments", "naive_baseline")
DATA = os.path.join(BASELINE_DIR, "data")

# make `import baseline` and `import mnemo...` both work regardless of caller cwd
for p in (BASELINE_DIR, IMPL):
    if p not in sys.path:
        sys.path.insert(0, p)

# The D3 baseline numbers to beat (from experiments/baseline_results.csv aggregate block).
BASELINE = {
    "overall_accuracy": 0.000,               # 0 / 11
    "supersession_failure_rate": 0.800,      # 4 / 5
    "cross_tenant_leak_rate": 0.500,         # F10-probed
    "cross_tenant_leak_queries": 7,          # of 11 (any foreign-tenant row in top-k)
    "pii_exposure_count": 3,
    "coldstart_abstention_failure_rate": 1.000,
}

# subject -> typed memory kind (what a real extractor would assign; here deterministic).
_TYPE_BY_SUBJECT = {
    "crm": "fact", "dm": "fact", "budget": "fact", "sso": "preference",
    "residency": "fact", "call_notes": "event",
}


def load_memories():
    with open(os.path.join(DATA, "memories.jsonl")) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_queries():
    with open(os.path.join(DATA, "queries.jsonl")) as f:
        return [json.loads(line) for line in f if line.strip()]


def mem_type_for(subject):
    return _TYPE_BY_SUBJECT.get(subject, "fact")


def raw_load_into_store(conn, memories):
    """[M1] Load every memory into the store with NO admission logic — one tenant-scoped
    repository per distinct tenant, seq = file order. Used by the isolation gate so G0 measures
    isolation alone, independent of the M2 write path. Returns {tenant_id: TenantRepository}."""
    from mnemo.repository import TenantRepository
    repos = {}
    for seq, m in enumerate(memories):
        t = m["tenant"]
        if t not in repos:
            repos[t] = TenantRepository(conn, t)
        repos[t].add_fact(
            id=m["id"], account=m["account"], subject=m["subject"],
            mem_type=mem_type_for(m["subject"]), text=m["text"],
            recorded_at=m["ts"], seq=seq, actor=m.get("user"),
            provenance=f'{m.get("tenant_name","")}:{m.get("user","")}',
        )
    conn.commit()
    return repos
