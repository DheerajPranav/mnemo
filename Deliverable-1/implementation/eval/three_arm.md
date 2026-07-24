# 3-arm comparison — naive · +recency · validity-filter (mnemo)

Same fixed set (44 memories / 11 queries, k=5, budget=2000). Only the mechanism differs.

| Metric | 1 naive | 2 +recency | 3 validity-filter |
|:--|:--:|:--:|:--:|
| overall_accuracy | 0.0 | 0.0 | **1.0** |
| recall_at_k | 0.333 | 0.333 | **0.778** |
| supersession_failure_rate | 0.8 | 0.8 | **0.0** |
| inversion_failures | 1 | 1 | **0** |
| cross_tenant_leak_queries | 7 | 10 | **0** |
| pii_exposure_count | 3 | 3 | **0** |
| coldstart_abstention_failure_rate | 1.0 | 1.0 | **0.0** |

## What arm 2 settles (the falsification test)
"Just prefer newer memories" is the cheap fix everyone reaches for. Measured on this set, it does **not** work — and it back-fires:

1. **Supersession is unchanged** (0.8 → 0.8). The stale chunk is the one that lexically matches the query ("CRM platform" appears in the *superseded* Salesforce memory; the current memory says "migrated to HubSpot"), so a recency bonus at any reasonable weight does not overcome the similarity gap. Recency competes with relevance instead of overriding it — which is exactly why validity belongs on the write path, not in the ranker.
2. **Cross-tenant leakage gets WORSE** (7 → 10 of 11 queries). The foreign-tenant near-duplicates (m101/m102, recorded Jan 2026) are *newer* than the tenant's own originals, so the recency signal actively promotes them. This is the D3 prediction — "a stronger ranking signal makes F10 worse, not better" — reproduced as a measurement.
3. **PII exposure and cold-start are untouched** (3 and 1.0). No ranking signal addresses either; one needs an admission gate, the other an abstain rule.

This settles first_principles falsifiers 1–2: supersession is **not** merely a recency-ranking problem, and the isolation / PII / cold-start failures are structural. Arm 3 fixes them by changing *what is allowed to be a candidate*, not by re-weighting.
