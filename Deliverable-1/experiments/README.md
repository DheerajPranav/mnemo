# experiments/

Deliverable 3: Productive Failure Baseline. **Complete** (run 22 July 2026).

The baseline implements Approach D from `../reconstruction/failure_analysis.md`: store every chunk,
retrieve top-k by a single similarity signal, inject in similarity order until a token budget is hit.
It is the strongest of the simpler approaches, so it is a fair baseline rather than a straw man.

## Artifacts (handbook section 5)

| Artifact | What it is |
| :-- | :-- |
| `naive_baseline/` | runnable code (pure stdlib) + committed seeded dataset — see its README |
| `baseline_protocol.md` | pre-registered method: hypothesis, workload, metric definitions, threats to validity |
| `baseline_results.csv` | per-query results + aggregate metric block |
| `error_examples.jsonl` | one concrete failure per line, with the retrieved evidence |
| `productive_failure_report.pdf` | the Appendix D report — measured results and interpretation |

Report source: `../_src/productive_failure_report.html` → rendered via `../../_build/topdf.sh`.

## Headline result

**0 of 11 queries pass.** The baseline is fast (p95 0.05 ms) and stays far under budget (92 of 2000
tokens), so its failures are *structural*, not a retrieval-tuning or cost problem. Measured failures:
supersession 0.80, cross-tenant leak on 7/11 queries, 3 PII exposures, 55.6% wasted top-k slots,
0/2 correct cold-start abstentions.

## What this settled

- Replaced two Deliverable 1 `[TO MEASURE]` tags with numbers: wasted-slot proportion (D-3) → **0.556**;
  single-signal supersession failure (D-1/B-3) → **0.80**.
- Reproduced 2 of Deliverable 1's 5 *unrecoverable* failures (F10 cross-tenant, F11 PII) — enough on
  their own to reject store-everything single-signal retrieval for a multi-tenant regulated setting.
- Out of scope for a retrieval-only baseline (deferred to Deliverable 6): F1, F2, F5, F6, F9. See
  `baseline_protocol.md` §7.
