# naive_baseline/

The deliberately-naive conversational-memory baseline for Deliverable 3 (Productive Failure
Baseline). It implements **Approach D** from `../../reconstruction/failure_analysis.md`: store every
chunk, retrieve top-*k* by a single similarity signal, inject in similarity order until a token
budget is hit — and *nothing else* (no admission control, no typed facts, no temporal validity, no
tenant partition, no abstention). Its failures are the measurement.

Pure Python standard library. No `pip install`, no network, no API key. Deterministic.

## Run it

```bash
python3 build_dataset.py     # regenerates data/*.jsonl deterministically (SEED=20260722)
python3 evaluate.py          # runs the baseline, writes results, prints the aggregate block
```

Outputs:

| File | What it is |
| :-- | :-- |
| `data/memories.jsonl` | 44 seeded GTM memories (1 PII, 3 foreign-tenant, 30 filler/dup) |
| `data/queries.jsonl` | 11 queries covering all six required workload conditions |
| `metrics.json` | machine-readable aggregate metrics |
| `../baseline_results.csv` | per-query rows + an aggregate block |
| `../error_examples.jsonl` | one concrete failure per line, with the retrieved evidence |

`data/*.jsonl` are committed, so the dataset is fixed even without re-running `build_dataset.py`;
that script documents *how* the dataset was constructed.

## Files

- `build_dataset.py` — deterministic dataset generator. Ground-truth conventions (memory `status`,
  query `gold` / `trap` / `probes`) are documented in its header.
- `baseline.py` — the retriever: `TfidfIndex` (one global index, no partition — by design),
  `budgeted_injection`, `tokenize`, `estimate_tokens`.
- `evaluate.py` — runs the baseline over the fixed set and measures each failure. Constants at the
  top (`K=5`, `TOKEN_BUDGET=2000`, `ABSTAIN_THRESHOLD=0.10` reference-only, `LATENCY_REPEATS=200`).

## What it measures, and what it can't

Measures the five failures a naive retriever actually produces — **F4** (superseded served as
current), **F7** (chunk inverts out of context), **F8** (index saturated with duplicates), **F10**
(cross-tenant leak), **F11** (sensitive data surfaced) — plus the **cold-start** abstention failure.

It does **not** exercise F1/F2 (need a multi-turn write path), F5/F6 (need a summariser), or F9
(needs delete-then-requery). Those are out of scope for a retrieval-only baseline and move to the
Deliverable 6 verification harness. Rationale in `../baseline_protocol.md` §7.

Full method, metric definitions, and threats to validity: **`../baseline_protocol.md`**.
Measured results and interpretation: **`../productive_failure_report.pdf`**.
