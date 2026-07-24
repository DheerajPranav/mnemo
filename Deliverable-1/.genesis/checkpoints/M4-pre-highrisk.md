# PRE-CHANGE CHECKPOINT — before M4 (lifecycle) · HIGH-RISK · 2026-07-25

> §7.3 evidence: checkpoint before a high-risk change. `design/sprint_plan.md` marks S3 as
> **"Risk: high — three capabilities cooperate; earliest adversarial testing."**

## Why high-risk
M4 is the first loop that **destroys and rewrites** state rather than only adding to it:
- **Hard deletion** removes rows and cascades to a derived projection. A bug here is unrecoverable
  data loss, and a *silent* bug looks identical to success (the row is gone either way).
- **Consolidation** is the classic F5/F6 failure surface: a rollup that *replaces* its sources
  destroys detail permanently and drifts from the truth. The design says CITE, never replace —
  and the naive implementation (write a rollup under the same `(account, subject)`) would trigger the
  M2 supersession rule and invalidate the very sources it summarises. **Prediction: if consolidation
  is admitted through the normal write path, gate G3(a) fails because the sources get invalidated.**
- **Correction** must leave a wrongly-invalidated fact recoverable (the ADR-001 residual).

## Restore point (state that is GREEN right now)
- Milestones DONE: M1 (G0 ✅), M2 (G1 ✅), M3 (G2 ✅ — 11/11).
- Tests green: 17/17 (`python3 -m unittest discover -s implementation/tests`).
- Gates green: `gate_g0_isolation.py`, `gate_g1_pii.py`, `gate_g2_baseline.py` — all exit 0.
- Files at restore point (do NOT touch on rollback): `mnemo/{store,repository,pii_gate,extraction,
  admission,retrieval,ranking,injection}.py`, `tests/test_{isolation,pii_gate,admission,ranking}.py`,
  `gates/{_dataset,gate_g0_isolation,gate_g1_pii,gate_g2_baseline}.py`, `eval/run_comparison.py`.
- **Rollback procedure if M4 regresses G0/G1/G2:** delete the M4-added files (`mnemo/{lifecycle,
  consolidation}.py`, `tests/test_lifecycle.py`, `gates/gate_g3_lifecycle.py`), revert the additive
  `store.py` tables and the additive `repository.py` methods; re-run G0+G1+G2 to confirm this restore
  point is intact; re-plan M4 with deletion split from consolidation.

## Freeze boundary for M4
`implementation/mnemo/{lifecycle,consolidation}.py` (new), **additive-only** changes to
`implementation/mnemo/{store,repository,admission}.py`, `implementation/tests/test_lifecycle.py`,
`implementation/gates/gate_g3_lifecycle.py`. Nothing else — in particular, the M3 read path
(`retrieval/ranking/injection`) is frozen so G2 cannot regress.

## Safety rule for this loop
Deletion is tested against a **throwaway in-memory store built from the fixed dataset**, never against
any file-backed database. `store.connect()` defaults to `:memory:`; the gate must not pass a path.
