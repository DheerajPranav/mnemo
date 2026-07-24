<div align="center">

# Mnemo

**The memory layer for GTM agents.**

*Durable, current, tenant-safe memory for conversational AI in B2B SaaS revenue teams.*

</div>

---

Mnemo is a **conversational-memory intelligence system**: the layer that lets an AI assistant
remember what's *true* about an account over time — durable across sessions, **current** (not merely
recent), **isolated** per tenant, and **safe** with sensitive data.

> The hard part of memory isn't storing things. It's knowing which stored thing is still *true*,
> keeping one customer's facts away from another's, and not remembering what you were never allowed to.

## Why it exists

A GTM assistant touches dozens of accounts a week and returns to any one after gaps of months. The
naive approaches fail in specific, *measurable* ways:

- a superseded fact ("Acme uses Salesforce") served as current after the world changed (they migrated to HubSpot);
- one customer's notes leaking into a different customer's near-identical "Acme" account;
- incidental PII stored by default and resurfaced on an unrelated question;
- the single buried dealbreaker ("data must stay in the EU") lost in a long thread.

Mnemo answers each with a **mechanism, not a hope**.

## The design in one line

Extract **typed, validity-stamped facts** at admission (PII-gated) → store them in a **single
transactional store** with tenant isolation as a **row-level invariant** → resolve conflicts on the
**write path** (not the ranker) → retrieve **tenant-isolated, currently-valid** facts into a
**budgeted, abstaining** injection — with every stage traced and the whole system measured against a
naive baseline.

## Status

Built as an 8-deliverable *Learning Through Reconstruction* engineering study — from first principles,
to a measured failure baseline, to a complete implementable system spec.

| # | Deliverable | Where | Status |
| :-- | :-- | :-- | :-- |
| **D1** | Problem Reconstruction | `Deliverable-1/reconstruction/` | ✅ |
| **D2** | Research-to-Design Scan | `Deliverable-1/research/` | ✅ (week 1) |
| **D3** | Productive Failure Baseline | `Deliverable-1/experiments/` | ✅ |
| **D4** | First-Principles System Design | `Deliverable-1/design/` | ✅ |
| **D5** | Genesis Engineering Workflow | `Deliverable-1/.genesis/` + `implementation/` | ✅ |
| **D6** | Implementation + Independent Verification | `Deliverable-1/implementation/` + `verification/` | ✅ |
| D7–D8 | Journal + Retrospective · Knowledge Transfer | — | ⏳ |

**Headline measured result (D3):** the naive single-signal baseline passes **0 / 11** adversarial
queries — supersession failure **0.80**, cross-tenant leak on **7/11**, **3** PII exposures — while
being fast (p95 ≈ 0.05 ms) and far under budget. The failures are **structural**, not a
retrieval-tuning problem, which is exactly what the D4 architecture is designed to fix.

**Headline built result (D5–D6):** the designed system — built across five bounded, gated Genesis loops —
passes **11 / 11** on the *same* fixed set: supersession **0.80 → 0**, cross-tenant leak **7/11 → 0**,
PII exposures **3 → 0**, cold-start abstention **1.0 → 0**. Every gate is a runnable script
(`implementation/gates/*.py`); isolation is a *constructor-scoped invariant* (no method can express a
cross-tenant read), conflict resolution lives on the write path, and injection abstains rather than
guesses.

**Independent verification (D6): PASS** — 8/8 executable handbook §8.3 acceptance checks over 38
evaluation cases, 36/36 tests, gates G0–G4 all green. Verification is re-derived *from the spec*
(`verification/verify.py` never reads the gates' own verdicts). A **3-arm comparison** falsifies the
cheap fix: adding a recency signal leaves supersession unchanged **and makes cross-tenant leakage
worse (7 → 10)** — these failures are structural, not ranking problems.

**Reported, not hidden.** Verification found that the write-path supersession rule had been silently
invalidating **31 of 40** memories (conversation turns were superseding each other), which meant an
earlier gate had been passing partly for the wrong reason; it is fixed, re-verified, and written up in
`verification/final_verification.pdf §4`. Four residual risks are carried with measured numbers —
including **R4**, where 3 subtle prompt injections survive admission and one was verified reaching an
injected context, and **R-P1**, where Postgres RLS ships as reviewable SQL but is marked **UNVERIFIED**
because no Postgres service was available to execute it.

Reproduce everything with no install / no network / no services:
```bash
cd Deliverable-1 && bash verification/run_all.sh
```

## Repository layout

```
Deliverable-1/          the project (all sub-deliverables in subfolders)
├── reconstruction/     D1 — problem, failure analysis, first-principles capabilities (C1–C10)
├── research/           D2 — research-to-design scan, ADRs, design backlog
├── experiments/        D3 — the naive baseline, dataset, measured results, failure report
├── design/             D4 — system design, architecture, data model, API, threat model, sprint plan
├── .genesis/           D5 — the Genesis spine (plan, definition-of-done, gates, checkpoints, decisions)
├── implementation/     D5→D6 — mnemo source (store, repository, admission, ranking, lifecycle, trace),
│                       36 tests, 5 runnable gates, 3-arm eval, Postgres+RLS schema
├── verification/       D6 — test plan, 38-case evaluation dataset, captured results, security report,
│                       final_verification.pdf  (run: bash verification/run_all.sh)
├── journal/            dated work-session notes
└── PROGRESS.md         running build log
_build/                 HTML → PDF render pipeline (headless Chrome + shared print CSS)
```

## Reproduce the baseline (D3)

```bash
cd Deliverable-1/experiments/naive_baseline
python3 build_dataset.py && python3 evaluate.py
```

Pure Python standard library — no install, no network, no API key. Deterministic (seed `20260722`);
every failure metric is byte-reproducible.

## Rebuild the PDFs

```bash
_build/topdf.sh Deliverable-1/_src/<name>.html Deliverable-1/<dest>/<name>.pdf
```

Requires Google Chrome (headless). The shared print styles live in `_build/print.css`.

---

<div align="center">

**Author:** Dheeraj Pranav
Built with AI assistance (Claude). The problem framing, design decisions, and every defensible
claim are the author's.

</div>
