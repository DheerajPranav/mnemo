# verification/

Deliverable 6: Independent Verification. **Complete** (25 July 2026). **Verdict: PASS** — 8/8
executable §8.3 acceptance checks over 38 evaluation cases, with 1 item reported UNVERIFIED.

Verification runs **from the specification and acceptance criteria** — `verify.py` re-derives every
check itself and never reads the gate scripts' verdicts. The maker does not grade itself.

## Artifacts (handbook §8.2)

| Artifact | What it is |
| :-- | :-- |
| `test_plan.md` | Test levels, the §8.3 check→evidence matrix, and every runnable command |
| `evaluation_dataset.jsonl` | 38 cases (11 retrieval · 8 PII pos/neg · 12 injection · 7 lifecycle/budget), each tagged with the §8.3 check it serves |
| `build_evaluation_dataset.py` | Deterministic rebuild of the dataset above |
| `verify.py` | The independent §8.3 harness — writes `results/verification_results.json` |
| `run_all.sh` | One command that reproduces and captures all evidence |
| `results/` | Captured outputs: unit tests, gates G0–G4, comparison, 3-arm, verification summary |
| `security_report.md` | Isolation, PII (positive+negative), deletion, prompt-injection red-team, residual register |
| `final_verification.pdf` | The verification report + verdict (source: `../_src/final_verification.html`) |

## Reproduce

```bash
cd Deliverable-1
bash verification/run_all.sh     # python3 stdlib only — no install, no network, no services
```

## Headline

The implemented system passes **11/11** adversarial queries on the fixed set the naive baseline passed
**0/11**: supersession failure 0.80→0, cross-tenant leak 7/11→0, PII exposures 3→0, cold-start
abstention 1.0→0. The 3-arm comparison shows a recency signal alone leaves supersession unchanged and
makes cross-tenant leakage *worse* (7→10) — the failures are structural, not ranking problems.

## Reported, not hidden

- **R4** — 3 subtle indirect-authority prompt injections survive admission; one verified reaching an injected context.
- **R-P1** — Postgres RLS ships as reviewable SQL but is **UNVERIFIED** (no Postgres service here; decision D6-DR-002).
- **R-P2** — spelled-out identifiers evade the deterministic PII floor.
- **R-P3** — subject-abbreviation queries abstain instead of answering (`recall_at_k` 0.778) — fails safe.

Also documented: this verification found that the write-path supersession rule had been silently
invalidating 31 of 40 memories, which meant Deliverable 5's read-path gate had been passing partly for
the wrong reason. Fixed, re-verified, and reported in `final_verification.pdf` §4.
