# Sprint Plan — Conversational Memory Intelligence System (v1)

**Deliverable:** 4 (System Design) · **Author:** Dheeraj Pranav · **Date:** 2026-07-22
**Feeds:** D5 (Genesis engineering workflow) · D6 (implementation + verification)
**Traces to:** milestones M1–M5 in `system_design.pdf` §11; `../research/design_backlog.md`.

Build order is chosen by **risk and dependency**, not by feature obviousness. Two rules set the
sequence: (1) the *unrecoverable* failures (F10, F11, F9) are closed **first**, because a leak or a
non-erasure in a demo is fatal and cheap to prevent early; (2) the *highest-risk* component gets the
earliest adversarial testing — `first_principles.md` §5 names **consolidation** (F5/F6, three
capabilities cooperating) as that component, so it is tested hard the moment it exists, not last.

Each sprint ends on an **acceptance gate** (the same tests listed in `system_design.pdf` §11 and
`api_contracts.md` §7). A sprint is not done until its gate is green in the eval harness.

---

## Sprint 0 — Scaffold & isolation skeleton (M1)  ·  closes A1/F10 first

**Goal:** the isolation invariant exists before any data does.
- Postgres schema from `data_model.md`: `memory`, `memory_embedding` (pgvector), `memory_source`,
  `access_log`, `deletion_request`, enums. Migrations checked in.
- Row-Level Security policies keyed on a session `tenant_id` GUC ([[ADR-005]]).
- Repository layer where `tenant_id` is a **constructor argument** — the type system forbids a
  cross-tenant method call.
- Embedding interface (one pinned provider model, swappable) — stub is fine here.

**Gate G0 (blocking):** the 4-vector cross-tenant adversarial suite (threat_model T1: forged param,
predicate-less raw query, mis-scoped repo, near-duplicate foreign memory) returns **zero** foreign
rows. Nothing proceeds until G0 is green.

**Depends on:** nothing. **Risk:** low, but foundational — a defect here poisons everything.

---

## Sprint 1 — Write path: extraction, PII gate, admission (M2)  ·  closes A2/F11

**Goal:** untrusted conversation becomes typed, screened, stored state.
- Extractor: turns → typed candidate claims (`type`, `subject`, `content`, `confidence`, `observed_at`).
- **PII gate** (Presidio deterministic-first, [[ADR-003]]) as a hard admission gate — blocked content
  never reaches the store.
- Op-selector (Mem0-style, **prototype**): store / update / discard vs current facts on
  `(account, subject)`; dedup (F8).
- Committer: `store` inserts; `update` runs the **supersession transaction** (invalidate prior, insert
  new — [[ADR-001]]).

**Gate G1:** (a) an admit containing a phone/medical token stores nothing for that candidate (F11);
(b) after a contradicting admit, the prior fact is `superseded`, still in the store, never re-injected
(F4); (c) a user `correct` writes at confidence 1.0 (F1).

**Depends on:** S0. **Risk:** medium — op-selector cost (threat R6) starts being measurable here.

---

## Sprint 2 — Read path: retrieve, rank, budget, abstain (M3)  ·  the correctness win

**Goal:** beat the D3 baseline on the fixed set.
- Tenant-scoped ANN over `memory_embedding`, **currently-valid only** (the ADR-001 validity filter).
- Multi-signal ranker: relevance + recency + importance-by-type + confidence, hand-specified weights
  in a visible config (C5).
- Budgeted, **position-aware** construction to ≤2000 tokens; **abstention floor** for cold-start (C6).

**Gate G2:** on the D3 fixed set — supersession-failure < baseline's 0.80, cross-tenant leak = 0
(vs 7/11), PII exposure = 0 (vs 3), cold-start abstains (vs 0/2), `used_tokens ≤ budget`. This is the
non-negotiable baseline-comparison gate (C10) with the numbers to beat already measured in D3.

**Depends on:** S0, S1. **Risk:** medium — this is where the design's core claim is proven or falsified.

---

## Sprint 3 — Lifecycle: consolidate, expire, delete (M4)  ·  highest-risk first + closes A3/F9

**Goal:** the store stays healthy and erasure is real.
- **Consolidation first and tested hardest** (`first_principles §5`): a rollup memory that **cites,
  never replaces** its sources (`consolidation_edge`), guarding F5 loss / F6 drift.
- Expiry/decay sweeps (validity-end, commitment-due, low-salience unused).
- Hard deletion: same-transaction cascade of `memory` + `memory_embedding`; `deletion_request` records
  the window.

**Gate G3:** (a) consolidation keeps every source retrievable and re-derivable (F5/F6); (b) delete-then-
requery is unretrievable within the ADR-004 window, `window_ms` recorded (F9); (c) an incorrectly
invalidated fact is recoverable from history (the ADR-001 residual).

**Depends on:** S1, S2. **Risk:** **high** — three capabilities cooperate; earliest adversarial testing.

---

## Sprint 4 — Observability & eval harness; injection hardening (M5)  ·  closes A5, opens R4

**Goal:** make every decision inspectable and every claim reproducible.
- `/trace/{id}`: per-request events (candidates, per-signal scores, budget drops, PII suppressions,
  final set) — C9. Audit write **fails closed** (threat R5): no result without an `access_log` row.
- Eval harness: the D3 dataset + LongMemEval scaffold ([[ADR-002]]) through the **3 arms**
  (naive / +recency / validity-filter), reporting component + end-to-end metrics.
- **Memory-borne prompt-injection red-team** (threat T4/R4): planted-instruction utterances; measure
  whether any survives extraction into an actionable injected memory.

**Gate G4:** (a) an injected failure in a test run is localised by its trace (C9); (b) the 3-arm report
reproduces byte-for-byte on the failure metrics; (c) zero planted instructions survive to an
actionable injected memory, or the residual is quantified and documented.

**Depends on:** S0–S3. **Risk:** medium; R4 is the genuinely open frontier.

---

## Sequencing & dependencies (summary)

```
S0 isolation ─▶ S1 write ─▶ S2 read ─▶ S3 lifecycle ─▶ S4 observ/eval/inject
   (G0 blocks)     (G1)        (G2 = beat baseline)   (G3 high-risk)   (G4)
```

- **Critical path:** S0 → S1 → S2 (a demonstrable, baseline-beating read path is the earliest
  end-to-end value).
- **Parallelisable:** the eval harness scaffold (S4) can be built alongside S1 since the D3 dataset
  already exists — only the 3-arm wiring waits on S2.
- **Unrecoverable-first ordering:** F10 (S0), F11 (S1), F9 (S3) are each closed *before* the sprint
  that would expose them at scale.

## Definition of done for D6 (what this plan hands off)
Every gate G0–G4 green in the eval harness; each acceptance test from `api_contracts.md` §7 automated;
the residual risk register (`threat_model.md` §4, R1–R6) either closed by a passing test or carried
forward with a measured number and an owner. The 3-arm comparison replaces the remaining D1
`to measure` tags and settles `first_principles.md` §6 falsifiers 1–2 (cheap, in-scope) and sets up
3–5 (need the full implementation).

## What feeds D5 (Genesis workflow)
This plan's sprint/gate structure is the input to the Genesis `.genesis/` spine initialisation (§7.2:
initialise after the design has a stable first version — now). Each gate G0–G4 becomes a Genesis
BUILD-loop checkpoint with maker≠checker verification; the acceptance tests are the checker's oracle.
