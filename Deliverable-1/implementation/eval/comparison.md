# Mnemo vs naive baseline — same fixed set (44 memories / 11 queries, k=5, budget=2000)

Baseline numbers: `experiments/naive_baseline/metrics.json` (D3). Mnemo numbers: full pipeline through the M1–M3 build loops.

| Metric | Baseline | Mnemo | Direction |
|:--|:--:|:--:|:--|
| overall_accuracy (pass rate, 11 queries) | 0.0 | **1.0** | ↑ higher better |
| recall_at_k | 0.333 | **0.778** | ↑ |
| supersession_failure_rate (F4) | 0.8 | **0.0** | ↓ lower better |
| inversion_failures (F7) | 1 | **0** | ↓ |
| cross_tenant_leak_queries (F10) | 7 | **0** | ↓ |
| pii_exposure_count (F11) | 3 | **0** | ↓ |
| coldstart_abstention_failure_rate | 1.0 | **0.0** | ↓ |

Every probed failure the read path is responsible for is closed (supersession, inversion, cross-tenant, PII, cold-start all at 0).

**Honest reading of recall_at_k (0.778).** After the D6/M4 fix, `event` memories (thread turns, chatter, call notes) correctly accumulate instead of superseding each other, so the ranker now competes against the full ~30-fact corpus rather than the 9 that survived the earlier write-path defect. Recall is therefore lower than the D5 run's 1.0 and *more honest*: the queries that miss are the subject-abbreviation ones (`dm` vs "decision maker"), where the current fact carries no lexical overlap with the query. The system abstains there rather than injecting a low-confidence answer, so no wrong answer is produced. Subject/query normalization is the tracked residual.
