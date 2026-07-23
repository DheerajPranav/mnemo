# Mnemo vs naive baseline — same fixed set (44 memories / 11 queries, k=5, budget=2000)

Baseline numbers: `experiments/naive_baseline/metrics.json` (D3). Mnemo numbers: full pipeline through the M1–M3 build loops.

| Metric | Baseline | Mnemo | Direction |
|:--|:--:|:--:|:--|
| overall_accuracy (pass rate, 11 queries) | 0.0 | **1.0** | ↑ higher better |
| recall_at_k | 0.333 | **1.0** | ↑ |
| supersession_failure_rate (F4) | 0.8 | **0.0** | ↓ lower better |
| inversion_failures (F7) | 1 | **0** | ↓ |
| cross_tenant_leak_queries (F10) | 7 | **0** | ↓ |
| pii_exposure_count (F11) | 3 | **0** | ↓ |
| coldstart_abstention_failure_rate | 1.0 | **0.0** | ↓ |

Every failure the read path is responsible for is closed. recall@k = 1.0 (every gold is retrieved into top-k). On q02/q06 the current fact (subject `dm`) is in top-k but its lexical confidence is below the abstain threshold, so the system abstains rather than inject a low-confidence answer — safe, but a documented residual: subject/query normalization (`dm` -> `decision maker`) is a D6 item.
