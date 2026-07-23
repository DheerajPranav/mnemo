# PRE-CHANGE CHECKPOINT — before M3 (read path) · HIGH-RISK · 2026-07-24

> Handbook §7.3 evidence: **a checkpoint created before a high-risk change.** M3 is the
> thesis-falsifying loop — `design/sprint_plan.md` marks G2 as "where the design's core claim is
> proven or falsified." A wrong ranker/validity interaction could make retrieval *worse* than the
> baseline (e.g. surface a superseded fact at rank 1). This file is the restore point so the change
> can be rolled back cleanly if G2 regresses.

## Why high-risk
- The read path is the first place three mechanisms interact live: validity filter (I3) × ranking × abstain (I4).
- The M2 write path shipped with a **known blind spot** (admission._supersedes v1 = later `recorded_at` wins; equal recorded_at resolves nothing). The SSO pair m005/m006 share `recorded_at = 2025-05-09`, so v1 leaves BOTH current. M3's gate is expected to expose this as an inversion failure (F7) on q04.
- Prediction (falsifiable): G2 will FAIL on first run with `inversion_failures = 1`, then pass after the fix.

## Restore point (state that is GREEN right now — roll back to this on regression)
- Milestones DONE: M1 (gate G0 ✅), M2 (gate G1 ✅).
- Tests green: 11/11 (`python3 -m unittest discover -s implementation/tests`).
- Gates green: `gate_g0_isolation.py` exit 0 (leak 0/11); `gate_g1_pii.py` exit 0 (pii 0).
- Files at restore point (do NOT touch on rollback):
  - `mnemo/{store,repository,pii_gate,extraction,admission}.py`
  - `tests/{test_isolation,test_pii_gate,test_admission}.py`
  - `gates/{_dataset,gate_g0_isolation,gate_g1_pii}.py`
- **Rollback procedure if M3 regresses G0/G1 or can't reach G2:** delete the M3-added files
  (`mnemo/{retrieval,ranking,injection}.py`, `tests/test_ranking.py`, `gates/gate_g2_baseline.py`,
  `eval/run_comparison.py`) and revert the one-line `admission._supersedes` change; re-run G0+G1 to
  confirm this restore point is intact; then re-plan M3 with a narrower ranker.

## Freeze boundary for M3
`implementation/mnemo/{retrieval,ranking,injection}.py`, `implementation/tests/test_ranking.py`,
`implementation/gates/gate_g2_baseline.py`, `implementation/eval/run_comparison.py`, and a **one-line**
change to `admission._supersedes` (the tiebreak) once the failure is confirmed. Nothing else.
