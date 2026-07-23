# implementation/

Runnable source for the designed system. Started under **Deliverable 5** (Genesis Engineering
Workflow): the first three build loops (M1–M3) were produced here as bounded, gated, independently
verified changes — this directory is D5's *workflow evidence* and the seed of **Deliverable 6**.

## What's built (D5 loops M1–M3)
| Module | Milestone | Invariant | Gate |
| :-- | :-- | :-- | :-- |
| `mnemo/store.py` | M1 | I5 (FK cascade), I6 (only file naming a DB driver) | — |
| `mnemo/repository.py` | M1 | **I1** tenant isolation (constructor-scoped) | G0 (leak 0/11) |
| `mnemo/pii_gate.py`, `extraction.py`, `admission.py` | M2 | **I2** PII hard gate, **I3** validity-on-write | G1 (pii 0) |
| `mnemo/retrieval.py`, `ranking.py`, `injection.py` | M3 | **I3** validity filter, **I4** budget/abstain | G2 (0/11 → 11/11) |

- **Gates** (`gates/*.py`) are runnable and compute the pass/fail against the *same fixed D3 dataset*
  the baseline was measured on — `gate_g0_isolation.py`, `gate_g1_pii.py`, `gate_g2_baseline.py`.
- **Tests**: `python3 -m unittest discover -s tests` — 17 tests.
- **Comparison**: `python3 eval/run_comparison.py` → `eval/comparison.md` (mnemo vs baseline).
- **Substrate**: pure-stdlib + `sqlite3` (decision `.genesis/decisions/D5-DR-001`). Production target is
  Postgres + pgvector + RLS (ADR-005), re-instated in D6 behind the same `TenantRepository`.

## Reproduce (no install, no network)
```bash
python3 -m unittest discover -s tests
python3 gates/gate_g0_isolation.py && python3 gates/gate_g1_pii.py && python3 gates/gate_g2_baseline.py
python3 eval/run_comparison.py
```

## Still to build (Deliverable 6, handbook §8.2)
Correction/deletion + expiration paths (M4, gate G3, high-risk), background consolidation/reflection,
decision traces + observability, the 3-arm eval, and the R4 memory-borne prompt-injection red-team (M5,
gate G4); plus the Postgres+pgvector+RLS migration.
