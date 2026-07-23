# D5-DR-001 — Implementation substrate for the Genesis build loops: pure-stdlib + sqlite3

- **Date:** 2026-07-24
- **Status:** accepted
- **Phase / milestone:** Deliverable 5 (Genesis Engineering Workflow), applies to M1–M3
- **Relates to:** ADR-005 (Postgres+pgvector single store) — this decision does **not** supersede it.

## Context
D4 specifies the production store as Postgres + pgvector with row-level security (ADR-005). The Genesis
build loops (M1–M3) must produce *inspectable changes that pass computed gates* in this environment,
which — like the D3 baseline environment — has no ability to install packages or run services (PEP-668
blocks `pip`; no local Postgres). Two things need proving in these three loops: (I1) tenant isolation is
an **invariant no method can express a violation of**, and (I3) the ranker only ever sees **currently-valid**
facts because conflict resolution happens on the **write path**. Both are *language-level / query-shape*
properties, not RLS-level properties.

## Decision
Build the M1–M3 loops in **pure standard-library Python over `sqlite3`**, and verify every gate against
the **same fixed D3 dataset** (`experiments/naive_baseline/data/`, `SEED=20260722`) the baseline was
measured on. Keep **Postgres + pgvector + RLS as the production substrate (ADR-005)**, re-instated in
Deliverable 6, where RLS becomes defence-in-depth *behind* the same constructor-scoped repository.

## Consequences
- Positive: gates are **computed, not narrated** — they run green here with zero install (same discipline as D3); the isolation invariant is proven faithfully because it is language-level; instant, reproducible feedback; a clean A/B against the baseline on identical data.
- Positive: sqlite `ON DELETE CASCADE` lets invariant **I5** (deletion cascade in one transaction) be demonstrated now, not just asserted.
- Negative / cost: RLS defence-in-depth is deferred to D6 (documented, not dropped). sqlite has no native vector search, so ranking uses the D3 lexical signal **plus the validity filter** rather than pgvector cosine — acceptable because the thesis is about *what the ranker is allowed to see*, not raw embedding quality (same argument as D3 protocol §2.1). A stronger embedder would make the *un*filtered baseline's F10 leak worse, not better, so lexical is a fair — even conservative — substrate for the claim.
- **Invariant added to context-graph.json:** none new; this decision is *how* I1–I6 are made testable on the loop substrate.

## Alternatives rejected
- **Postgres-first (ADR-005 verbatim in the loops)** — needs a running Postgres this environment can't provide; heavy dependency to prove a language-level invariant; slow per-loop feedback. (PLAN.md Approach A.)
- **Mock/spec-only harness** — proves nothing; gates would be narrated not computed, the exact anti-pattern `LOOPS.md` forbids; can't beat a baseline you never ran. (PLAN.md Approach C.)
