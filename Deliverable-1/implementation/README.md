# implementation/ — Mnemo

Runnable source for the conversational-memory system designed in Deliverable 4. Built across five
bounded Genesis build loops (M1–M3 in Deliverable 5, M4–M5 in Deliverable 6), each shipped behind a
computed gate with independent verification.

## Setup

**None.** Python 3.8+ standard library only — no `pip install`, no network, no services, no API key.
(Substrate decision `D5-DR-001` / `D6-DR-002`: the loops run on `sqlite3`; the production substrate is
Postgres + pgvector + RLS, shipped as `mnemo/postgres_schema.sql`, not executed here.)

```bash
cd Deliverable-1
python3 -m unittest discover -s implementation/tests    # 36 tests
bash verification/run_all.sh                            # everything, with evidence captured
```

## Architecture summary

```
                 TRUST BOUNDARY TB-1 (untrusted conversation text)
                                  │
   admit(record) ─► pii_gate ─► injection_guard ─► extraction ─► repository.add_fact
                     (I2)          (T4/R4)         (typed)        + invalidate superseded (I3)
                                                                  + embedding (derived projection)
                 TRUST BOUNDARY TB-2 (tenant isolation, I1)
                                  │
   retrieve(q) ─► repository.current_facts ─► ranking ─► injection ─► access_log (I9, fails closed)
                  tenant-scoped + valid only    multi-signal   budget + abstain      + Trace (C9)

   lifecycle: delete (cascade + measured window, I7) · correct/restore · expire_events
   consolidation: rollup CITES sources via consolidation_edge, never replaces (I8)
```

The load-bearing idea: **failures are made unreachable upstream, not filtered downstream.** A
superseded, foreign-tenant, or PII memory is never a *candidate*, so no query — not even one quoting
its exact text — can rank it into the answer.

| Module | Milestone | Invariant | Gate |
| :-- | :-- | :-- | :-- |
| `mnemo/store.py` | M1/M4 | I5/I7 cascade, I6 only file naming a driver | — |
| `mnemo/repository.py` | M1 | **I1** tenant is a constructor arg, never a parameter | G0 |
| `mnemo/pii_gate.py`, `extraction.py`, `admission.py` | M2 | **I2** hard PII gate, **I3** validity-on-write | G1 |
| `mnemo/retrieval.py`, `ranking.py`, `injection.py` | M3 | **I3** validity filter, **I4** budget/abstain | G2 |
| `mnemo/lifecycle.py`, `consolidation.py` | M4 | **I7** deletion is real, **I8** cite-never-replace | G3 |
| `mnemo/trace.py`, `injection_guard.py` | M5 | **I9** audit fails closed; T4/R4 | G4 |
| `mnemo/postgres_schema.sql` | D6 | production substrate + RLS (**not executed here**) | — |

## Commands

| Command | Proves |
| :-- | :-- |
| `python3 implementation/gates/gate_g0_isolation.py` | cross-tenant leak 7/11 → **0/11** |
| `python3 implementation/gates/gate_g1_pii.py` | PII exposures 3 → **0** |
| `python3 implementation/gates/gate_g2_baseline.py` | accuracy 0/11 → **11/11** vs the D3 baseline |
| `python3 implementation/gates/gate_g3_lifecycle.py` | consolidation cites 12/12 · deletion real + window measured · correction recoverable |
| `python3 implementation/gates/gate_g4_observability.py` | trace localises an injected failure · audit fails closed · 8/8 overt injections blocked |
| `python3 implementation/eval/run_comparison.py` | mnemo vs baseline → `eval/comparison.md` |
| `python3 implementation/eval/run_3arm.py` | naive / +recency / validity arms → `eval/three_arm.md` |
| `python3 verification/verify.py` | the §8.3 acceptance checks, independently re-derived |

## Results (same fixed set: 44 memories / 11 queries, k=5, budget=2000)

| Metric | Naive baseline | Mnemo |
| :-- | :--: | :--: |
| overall_accuracy | 0.000 | **1.000** |
| supersession_failure_rate | 0.800 | **0.000** |
| cross_tenant_leak_queries | 7 | **0** |
| pii_exposure_count | 3 | **0** |
| coldstart_abstention_failure_rate | 1.000 | **0.000** |

## Known limitations (see `../verification/security_report.md`)
- **R4** — subtle indirect-authority prompt injections survive admission (3/3); one reaches context.
- **R-P1** — Postgres RLS is shipped but **unverified** here (no Postgres service).
- **R-P2** — spelled-out identifiers evade the deterministic PII floor.
- **R-P3** — subject-abbreviation queries abstain rather than answer (`recall_at_k` 0.778) — fails safe.
