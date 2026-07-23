# PLAN — Mnemo

The machine-parseable implementation plan. Mirrors the milestone table in `DONE.html` (DONE.html is the
human/visual view; this is the one loops read). Sliced so each milestone ships in one L1 BUILD pass.

> Slicing rule: a milestone must have (a) a single clear outcome, (b) an exact **demo command** that
> proves it, and (c) a freeze boundary of files it may touch. If you can't write the demo command,
> the milestone is too vague — split it.

> **Seeded from the D4 design.** The milestones ARE the first three sprints of `design/sprint_plan.md`
> (S0→S1→S2); the gates are that plan's acceptance gates G0→G2; the numbers-to-beat are the *measured*
> D3 baseline (`experiments/baseline_results.csv`). Nothing here is invented — D5 executes the D4 plan
> as bounded, verifiable loops.

---

## Brainstorm (G0.5 — three approaches to the cognitive job, one chosen)

> Cognitive job (from DONE.html §1): keep a durable, current, tenant-isolated, PII-safe memory and
> select the currently-valid subset into a bounded window. The design question this build must settle:
> **where does isolation + validity live, and on what substrate do the loops actually run?**

### Approach A — "Postgres-first, exactly as ADR-005 specifies"
Stand up real Postgres + pgvector + row-level security (RLS) and build the loops against it, so the
implementation substrate == the production substrate with no translation.
- Strengths: zero design drift from D4; RLS is defence-in-depth the loops can actually exercise.
- Weaknesses: needs a running Postgres in the loop environment (this box has `pip`/services blocked, mirroring the D3 PEP-668 constraint); a heavy dependency to prove a language-level invariant; slower per-loop feedback.

### Approach B — "Isolation as a library invariant on a stdlib substrate" ✅
Build the load-bearing mechanism — the **constructor-scoped repository** (no method can *express* a
cross-tenant read) and the **write-path validity filter** — in pure-stdlib Python over `sqlite3`, and
verify every gate against the *same fixed D3 dataset* the baseline was measured on. Postgres+pgvector +
RLS remain the production target (ADR-005), recorded as a substrate decision, added back in D6.
- Strengths: the loops run green here with zero install (same discipline as D3); the thing being proven — that isolation is an *invariant no method can violate* — is language-level, not RLS-level, so sqlite proves it faithfully; instant, reproducible gate feedback; a clean A/B against the baseline on identical data.
- Weaknesses: RLS defence-in-depth is deferred (documented, not dropped); sqlite lacks native vector search, so ranking uses the D3 lexical signal + validity filter rather than pgvector cosine (the thesis is about *what the ranker is allowed to see*, not raw embedding quality — same argument as D3 §2.1).

### Approach C — "Mock everything; assert the failures are fixed in a spec harness"
Skip a real store; write a harness that stubs retrieval and asserts the design *would* fix F4/F10/F11.
- Strengths: fastest to write; no substrate at all.
- Weaknesses: proves nothing — gates would be *narrated, not computed*, exactly the anti-pattern LOOPS.md forbids; no inspectable change; can't beat a baseline you never actually ran against.

### Chosen: **Approach B** — the load-bearing claims (isolation-as-invariant, validity-on-write) are
language-level and provable on a stdlib/sqlite substrate against the identical D3 fixed set, giving
computed (not narrated) gates with instant reproducible feedback; the Postgres+pgvector+RLS production
substrate is preserved as ADR-005 and re-instated in D6. Recorded as **decision D5-DR-001**.

---

## Milestones

### M1 — Tenant isolation (S0) — constructor-scoped repository + store
- **Outcome:** a `TenantRepository` whose tenant is a constructor argument, never a method parameter; every read/write scoped to it. On the D3 fixed set, retrieval returns **0** foreign-tenant rows.
- **Phase (swe-master):** modular-architecture / data-systems
- **Files / freeze boundary:** `implementation/mnemo/{store,repository}.py`, `implementation/tests/test_isolation.py`, `implementation/gates/gate_g0_isolation.py`
- **Demo command:** `python3 implementation/gates/gate_g0_isolation.py`
- **Success criteria:** Gate **G0** green — cross-tenant leak rate = 0 across all 11 queries (baseline: 7/11); invariant **I1** holds (a static check confirms no repository method signature takes `tenant_id`). Blocking: nothing proceeds until G0 is green.
- **Loops:** L1, L4
- **Skills:** canon + tdd + data-systems-engineering
- **Token budget:** 50000

### M2 — Write path (S1) — typed extraction + PII admission gate + provenance
- **Outcome:** an `admit()` path that extracts typed facts, runs a deterministic PII gate as a **hard precondition**, and persists with provenance + bi-temporal validity (invalidating superseded facts on write).
- **Phase:** LLMOps / security-engineering
- **Files:** `implementation/mnemo/{extraction,pii_gate,admission}.py`, `implementation/tests/test_pii_gate.py`, `implementation/tests/test_admission.py`, `implementation/gates/gate_g1_pii.py`
- **Demo command:** `python3 implementation/gates/gate_g1_pii.py`
- **Success criteria:** Gate **G1** green — an admit containing a phone/medical token stores nothing for that candidate; PII exposure count = **0** (baseline: 3); invariant **I2** holds (blocked content leaves no row, no log payload).
- **Loops:** L1, L3 (research: Presidio recognizer set), L4
- **Skills:** canon + tdd + security-engineering + llmops-ai-agents
- **Token budget:** 50000

### M3 — Read path (S2) — validity-filtered multi-signal ranker, beat the D3 baseline
- **Outcome:** a `retrieve()` path that fetches only tenant-scoped, currently-valid candidates, ranks them with a hand-specified multi-signal score, and injects within a token budget or **abstains**.
- **Phase:** retrieval & ranking / evaluation
- **Files:** `implementation/mnemo/{retrieval,ranking,injection}.py`, `implementation/tests/test_ranking.py`, `implementation/gates/gate_g2_baseline.py`, `implementation/eval/run_comparison.py`
- **Demo command:** `python3 implementation/gates/gate_g2_baseline.py`
- **Success criteria:** Gate **G2** green — on the D3 fixed set, supersession-failure **< 0.80** AND cross-tenant leak = **0**; invariants **I3** (validity filter) + **I4** (budget/abstain) hold. This is the thesis-falsifying change → **checkpoint before it**; **document the real recovery** if the first ranker formulation fails a gate.
- **Loops:** L1, L2 (debug — expected here), L4
- **Skills:** canon + tdd + evaluation
- **Token budget:** 50000

<!-- M4 (S3 lifecycle, high-risk, gate G3) and M5 (S4 observability/eval/injection, gate G4) are deferred to Deliverable 6 per the D5↔D6 boundary. -->

---

## Progress (loops append here on milestone completion — newest last)

- **M1 — tenant isolation (S0) · DONE · 2026-07-24.** Gate G0 PASS (exit 0): cross-tenant leak **7/11 → 0/11**; F10-probed leak rate 0.500 → 0.000. Invariant I1 verified two ways (static: no method signature carries a tenant; adversarial L4: 9/9 attacks blocked). Files: `mnemo/{store,repository}.py`, `tests/test_isolation.py`, `gates/{_dataset,gate_g0_isolation}.py`. Checkpoint: `checkpoints/M1.md`.
- **M2 — write path + PII gate (S1) · DONE · 2026-07-24.** Gate G1 PASS (exit 0): PII exposures **3 → 0**; exactly 1 record blocked (m009), zero over-blocks across all 44. Invariant I2 verified (blocked leaves no row/embedding/log; L4 3/3 attacks handled) + honest residual logged (spelled-out numbers → D6 Presidio ML). Files: `mnemo/{pii_gate,extraction,admission}.py`, `tests/{test_pii_gate,test_admission}.py`, `gates/gate_g1_pii.py`. Checkpoint: `checkpoints/M2.md`.
- **M3 — read path, beat the baseline (S2) · DONE · 2026-07-24 · HIGH-RISK.** Gate G2 PASS (exit 0): **overall accuracy 0/11 → 11/11**, recall@k 0.333 → 1.0, supersession 0.80 → 0.0, inversion 1 → 0, leak 7 → 0, PII 3 → 0, cold-start 1.0 → 0.0. **Documented recovery (§7.3):** first G2 run failed on the predicted SSO same-`recorded_at` tie (F7) *and* an unpredicted cold-start abstain miss; root-caused via L2 DEBUG into 5 principled revisions (R1 seq-tiebreak, R2 stopwords+subject-slot, R3 account-name strip, R4 single-char drop, R5 same-account abstain); pre-change restore point `M3-pre-highrisk.md` held G0/G1 green throughout. L4 4/4 adversarial attacks blocked. Files: `mnemo/{retrieval,ranking,injection}.py`, `tests/test_ranking.py`, `gates/gate_g2_baseline.py`, `eval/run_comparison.py`. Checkpoints: `M3-pre-highrisk.md`, `M3.md`.
