# ADR-005: Postgres + pgvector single-store, with tenant isolation as a row-level invariant

**Status:** accepted (v1 scope; tier-bound to ADR-004)
**Date:** 2026-07-22
**Deliverable:** D4 (System Design).
**Traces to:** capabilities C4 (source-of-truth vs index), C8 (isolation invariant); premises P5, P6, P8;
failures F9, F10; [[ADR-004]].

## Context
C4 requires an authoritative store with the retrieval index as a *derived, rebuildable projection*, so
that deletion is authoritative (F9) and an embedding-model change is a re-projection, not a migration.
C8 requires tenant isolation as an **invariant** — "no query path can express a cross-tenant read"
(F10) — not a post-retrieval filter. D1 §4 originally implied a dual store (separate vector DB), which
introduces a deletion **consistency window** between the two stores. At the ADR-004 small/team scale
(~2 × 10⁶ facts) we can do better.

## Decision drivers
- F10 is one of the five *unrecoverable* failures and D3 measured it leaking on **7/11** queries with a
  post-hoc filter mindset — isolation must be structural, not remembered.
- F9 (deleted-yet-retrievable) is unrecoverable and its risk is dominated by the *gap* between deleting
  the source row and deleting the index vector.
- ADR-004: the corpus fits one Postgres instance.

## Options considered
1. **Dual store: Postgres (truth) + dedicated vector DB (index).** Scales to mid-market; but
   reintroduces the cross-store deletion window (F9 surface) and a second isolation boundary to enforce
   (F10 surface). Overkill at 2 × 10⁶ facts.
2. **SQLite + in-process vector index.** Simplest; but weak concurrency, no row-level security, and a
   poor fit for a multi-tenant SaaS control plane.
3. **Single Postgres instance: facts + pgvector index in the same transactional database (chosen).**

## Decision
Adopt **option 3**.
- **Source of truth:** a `memory` table (typed facts, validity fields, provenance) — see
  `../data_model.md`.
- **Retrieval index:** a `memory_embedding` table with a `pgvector` HNSW index, treated as a derived
  projection of `memory`. Rebuildable by re-embedding fact rows; an embedding-model swap is an
  `UPDATE`, not a migration (satisfies C4/P8).
- **Deletion (F9):** deleting a fact deletes its embedding **in the same transaction** → the typical
  consistency window collapses to a single transaction (near-synchronous), with the ADR-004 24 h
  figure kept only as a backstop for the async re-index edge case.
- **Isolation (C8/F10):** `tenant_id` is a mandatory column on every table and is enforced two ways:
  (1) **Postgres Row-Level Security** policies keyed on a session `tenant_id` GUC, so a raw query
  cannot read another tenant's rows even if it forgets the predicate; (2) a repository layer where
  `tenant_id` is a **constructor argument of the data-access object, never a method parameter** — so no
  method signature in the codebase can express a cross-tenant read. Every read is written to
  `access_log`.

## Consequences and trade-offs
- (+) Deletion is authoritative and near-synchronous; the F9 window is a transaction, not a job.
- (+) Isolation is defence-in-depth: an application bug is caught by RLS; an RLS misconfig is caught by
  the constructor-scoped repository. Adversarial cross-tenant tests (C10) target *both* layers.
- (+) One system to operate, back up, and reason about at this tier.
- (−) **Tier-bound.** Does not scale to the D1 mid-market 10⁸ figure; pgvector HNSW recall/latency
  degrade well before that. The scale-up path is option 1, which *reintroduces* the deletion window —
  so the F9 guarantee is explicitly a property of the small/team tier, and revisited with ADR-004.
- (−) pgvector ties the index to Postgres; the swappable-embedding-interface (D1 non-goal) is honoured
  at the *model* boundary, not the *index-engine* boundary in v1.

## Validation plan (D6)
- Adversarial cross-tenant suite (the D3 F10 cases, expanded): attempt cross-tenant reads via the API,
  via a raw query with the predicate omitted (must be blocked by RLS), and via a mis-scoped repository
  (must be impossible to construct). All must return zero foreign rows.
- Deletion window measured under load: delete-then-requery latency distribution; assert p100 within the
  guaranteed window.

## Revisit conditions
- **Reverse to option 1** when ADR-004's revisit triggers fire (a tenant nears 10⁵ memories, or a
  second region is added). At that point re-open the C4 deletion-window design as a first-class problem.
