# Test Plan — Mnemo (Deliverable 6)

**Scope.** Verify the implemented system against the handbook §8.3 minimum acceptance checks, the D4
specification (`design/`), and the measured D3 baseline. Verification is performed **from the
specification**, not by accepting the implementation's own assessment: `verification/verify.py`
re-derives each check independently and never reads the gate scripts' verdicts.

**Principle.** Every claim in this plan is either backed by a command whose exit code you can
reproduce, or it is listed as **UNVERIFIED**. There is no third category.

---

## 1. How to run everything

```bash
# from Deliverable-1/ — no install, no network, no services (Python 3.8+ stdlib only)
bash verification/run_all.sh
```
Captures all evidence under `verification/results/`. Individual pieces:

| Command | What it proves |
| :-- | :-- |
| `python3 -m unittest discover -s implementation/tests` | 36 unit/integration tests |
| `python3 implementation/gates/gate_g0_isolation.py` | G0 — tenant isolation (blocking) |
| `python3 implementation/gates/gate_g1_pii.py` | G1 — PII admission gate |
| `python3 implementation/gates/gate_g2_baseline.py` | G2 — read path beats the D3 baseline |
| `python3 implementation/gates/gate_g3_lifecycle.py` | G3 — consolidation / deletion / correction |
| `python3 implementation/gates/gate_g4_observability.py` | G4 — traces, reproducibility, injection |
| `python3 implementation/eval/run_comparison.py` | mnemo vs baseline table |
| `python3 implementation/eval/run_3arm.py` | naive / +recency / validity-filter arms |
| `python3 verification/verify.py` | the §8.3 checks, independently re-derived |

## 2. Test levels (proportional to risk, per §8.2)

| Level | Where | Notes |
| :-- | :-- | :-- |
| Unit | `implementation/tests/test_{pii_gate,ranking,admission}.py` | recognizers, ranker signals, supersession rule |
| Integration | `test_{lifecycle,trace}.py` | write→read→lifecycle across store + repository |
| End-to-end | `gates/gate_g2_baseline.py`, `gate_g3_lifecycle.py` | full admit→retrieve→inject on the fixed set |
| Evaluation | `eval/run_comparison.py`, `eval/run_3arm.py` | metric comparison against the measured baseline |
| Performance | `gate_g2` (latency context), `gate_g3` (`window_ms`) | deletion window measured, not asserted |
| Security | `test_red_team.py`, `verify.py` checks 3/6/R4, `security_report.md` | isolation, PII, prompt injection |

## 3. §8.3 acceptance checks → evidence

| # | §8.3 check | How it is verified (independent) | Evidence | Result |
| :-- | :-- | :-- | :-- | :-- |
| 1 | Relevant memories outrank plausible distractors | For each of the 11 fixed queries, assert the distractor never precedes the gold in the ranking. (Stronger outcome observed: distractors are removed upstream by validity/isolation/PII, so they cannot rank at all.) | `verify.py::check_1` | **PASS** |
| 2 | Stale/superseded preferences do not override current | (i) m001/m003/m005/m007 are not current; (ii) the current fact is the one injected for q01/q03/q04; (iii) a wrongly-invalidated fact is recoverable | `verify.py::check_2`, `gate_g2`, `gate_g3(c)` | **PASS** |
| 3 | No cross-tenant memory under adversarial queries | All 11 queries + **exact-text** adversarial queries for m101/m102 + a static check that no repository method accepts a tenant parameter | `verify.py::check_3`, `gate_g0` | **PASS** |
| 4 | Deletion removes from source storage and retrieval within the documented window | delete→re-query returns nothing; **raw SQL** confirms 0 rows in `memory` and `memory_embedding`; `deletion_request.window_ms` recorded and ≤ ADR-004 24h backstop | `verify.py::check_4`, `gate_g3(b)` | **PASS** |
| 5 | Context selection respects the configured token budget | Retrieval at budgets 40 / 120 / 2000; measured injected tokens ≤ budget in each case | `verify.py::check_5` | **PASS** |
| 6 | Sensitive-data policy tested with positive **and** negative cases | 4 positive (phone, health, email, SSN) must block and must not retain the raw span; 4 negative (money, ISO date, vendor, policy) must be admitted; flagged m009 must be absent from the store | `verify.py::check_6`, `test_pii_gate.py` | **PASS** |
| 7 | Benchmark results compared with the naive baseline | mnemo vs the D3 `metrics.json` on every failure metric, plus the 3-arm comparison | `verify.py::check_7`, `eval/*` | **PASS** |
| + | *(project-specific)* Memory-borne prompt injection (T4/R4) | 12-case red-team corpus: overt injections must block, benign control must be admitted, surviving subtle cases must be **quantified** | `verify.py::check_8`, `test_red_team.py`, `gate_g4(c)` | **PASS** (with documented residual) |

## 4. Explicitly UNVERIFIED (reported, not assumed)

| Item | Why | How to close |
| :-- | :-- | :-- |
| ADR-005 Postgres + pgvector + **RLS** substrate | No Postgres service is available in this environment (decision `D6-DR-002`). The schema and RLS policies ship as `implementation/mnemo/postgres_schema.sql` but are **not executed**. | `psql -f implementation/mnemo/postgres_schema.sql`, then `SET LOCAL app.tenant_id = '<A>'` and confirm `SELECT count(*) FROM memory WHERE tenant_id='<B>'` returns 0 |
| pgvector ANN recall behaviour | Ranking evidence here uses the lexical signal (D5-DR-001, D3 §2.1). | Re-run `gate_g2` against the Postgres substrate with embeddings |

## 5. Known limitations carried forward (not hidden)
- **R4 residual:** 3 of 3 "subtle indirect-authority" injections survive admission and 1 (`rt09`) reaches an injected context. Quantified in `security_report.md`.
- **Subject-abbreviation recall:** queries phrased as "decision maker" do not lexically match the `dm` subject slot, so the system **abstains** rather than answering (no wrong answer produced). `recall_at_k = 0.778`.
- **PII floor:** spelled-out identifiers ("five five five…") evade the deterministic recognizers; production adds Presidio's ML layer (ADR-003).

## 6. Determinism
Fixed dataset (`SEED=20260722`), fixed k=5 and budget=2000, no randomness at evaluation time. The
3-arm failure metrics are asserted byte-identical across two runs by `gate_g4(b)`. Only wall-clock
figures (`window_ms`, latency) vary between runs.
