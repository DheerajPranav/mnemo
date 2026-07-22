# Data Model — Conversational Memory Intelligence System (v1)

**Deliverable:** 4 (System Design) · **Author:** Dheeraj Pranav · **Date:** 2026-07-22
**Envelope:** small/team tier ([[ADR-004]]) · **Storage:** single Postgres + pgvector ([[ADR-005]])
**Traces to:** C3 (typed representation), C4 (truth vs index), C7 (lifecycle), C8 (isolation),
C9 (observability) — `../reconstruction/first_principles.md`.

This is the authoritative schema. Every field exists to serve a capability, an invariant, or a
measured failure; the "why" column names it. Types are Postgres types; a swap of engine keeps the
logical model. Raw conversation transcripts are **not** owned by this system (D1 non-goal — only
information *observed in* conversation is stored, via provenance references).

---

## 1. Entities and relationships

```
tenant 1───∞ account 1───∞ memory ∞───1 memory_type
                              │ 1
                              ├──── ∞ memory_source     (provenance; how deletion finds every copy)
                              ├──── 1 memory_embedding   (derived index projection — rebuildable)
                              └──── ∞ consolidation_edge (cite-don't-replace links)
tenant 1───∞ access_log                (every read, for audit — C9)
tenant 1───∞ deletion_request          (erasure jobs, measures the F9 window — C7)
```

Supersession is a self-relation on `memory` (`invalidated_by`), not a separate table: a contradicting
fact invalidates the prior one in place (bi-temporal, [[ADR-001]]).

---

## 2. `memory` — the source of truth (typed facts)

One row per **resolved claim** (not per utterance — C3, fixes F7). Content is an extracted, typed,
context-free statement.

| Column | Type | Why (capability / failure / premise) |
| :-- | :-- | :-- |
| `id` | `uuid` PK | identity for provenance + tracing (C9) |
| `tenant_id` | `uuid` NOT NULL | **isolation invariant** (C8/F10); RLS + repo scope key ([[ADR-005]]) |
| `account_id` | `uuid` NOT NULL | GTM scoping — memories are about an account |
| `user_id` | `uuid` NULL | author/owner of the observation; NULL = tenant-shared (non-goal in v1) |
| `type` | `memory_type` enum | drives importance + supersession scope (C5); see §3 |
| `subject` | `text` NOT NULL | the entity/attribute the claim is about, e.g. `acme:crm` — supersession key |
| `content` | `text` NOT NULL | the resolved claim, PII-screened before insert (C2/F11) |
| `confidence` | `real` 0–1 NOT NULL | ranking signal + drift guard (C3/C5); corrections = 1.0 (C1) |
| `observed_at` | `timestamptz` NOT NULL | when it was said (world-time anchor) |
| `valid_from` | `timestamptz` NOT NULL | world-time validity start (P4) |
| `valid_to` | `timestamptz` NULL | world-time validity end; **NULL = currently valid** (F4) |
| `recorded_at` | `timestamptz` NOT NULL | system-time: when we learned it (bi-temporal, [[ADR-001]]) |
| `invalidated_at` | `timestamptz` NULL | system-time: when superseded; NULL = live |
| `invalidated_by` | `uuid` NULL FK→memory | the fact that superseded this one (audit chain, C7/C9) |
| `status` | `memory_status` enum | `current \| superseded \| expired \| deleted` (derived, indexed) |
| `salience` | `real` 0–1 NOT NULL | admission importance score (C2/F8); low + unused → decays (C7) |
| `pii_screened` | `bool` NOT NULL | true once the admission PII gate has passed it (C2/F11, [[ADR-003]]) |
| `created_at` / `updated_at` | `timestamptz` | row bookkeeping |

**Invariants**
- A retrieval query returns a memory **only if** `status='current'` AND `valid_to IS NULL` AND
  `invalidated_at IS NULL` (the validity filter — moves conflict resolution off the ranker, ADR-001).
- Writing a superseding fact is a **transaction**: insert the new `current` fact, set the prior fact's
  `valid_to`, `invalidated_at`, `invalidated_by`, `status='superseded'`. Never delete on supersession
  (history preserved for C4/C7/C9).
- `content` is never inserted before `pii_screened = true`. There is no post-hoc redaction path.

**Indexes:** `(tenant_id, account_id, status)`, `(tenant_id, subject, status)`, `(valid_to)` partial
where NULL. All reads are tenant-scoped first.

---

## 3. `memory_type` and supersession scope

The enum drives two things: a default **importance** prior for ranking (C5), and the **supersession
key** — a new fact supersedes prior *current* facts sharing the same `(account_id, subject)` within a
supersession-eligible type.

| `memory_type` | Example (GTM) | Importance prior | Supersedes on match? |
| :-- | :-- | :-- | :-- |
| `account_attribute` | CRM platform, budget, region | high | yes — single-valued per subject |
| `stakeholder` | decision maker, primary contact | high | yes |
| `requirement` | SSO for prod, EU data residency (dealbreaker) | **highest** | additive; withdrawn → invalidate |
| `preference` | prefers async demos | medium | yes |
| `commitment` | next step, follow-up owed | medium | expires at due date (C7) |
| `meeting_note` | neutral call summary | low | no — additive log |

`requirement` gets the highest prior because D1/D3 showed the single buried dealbreaker (EU residency,
`m020`) is the case importance-aware selection exists for (C6/F3).

---

## 4. `memory_source` — provenance (C3, C4, C7)

| Column | Type | Why |
| :-- | :-- | :-- |
| `id` | `uuid` PK | |
| `memory_id` | `uuid` FK→memory | the claim this evidence supports |
| `session_id` | `uuid` NOT NULL | conversation reference (external transcript store) |
| `turn_id` | `uuid` NOT NULL | the specific turn |
| `char_span` | `int4range` | span within the turn, for re-derivation |
| `observed_at` | `timestamptz` | redundant anchor for audit |

Provenance is what makes consolidation **safe** (re-derivable) and deletion **complete** (find every
copy). A consolidated memory keeps the source rows and cites them — it never replaces them (C7, avoids
reintroducing F5/F6).

---

## 5. `memory_embedding` — derived index projection (C4, [[ADR-005]])

| Column | Type | Why |
| :-- | :-- | :-- |
| `memory_id` | `uuid` PK FK→memory (ON DELETE CASCADE) | cascade = deletion window collapses to a txn (F9) |
| `tenant_id` | `uuid` NOT NULL | isolation carried into the index (C8) — RLS applies here too |
| `model_id` | `text` NOT NULL | which embedding model produced this (pinned; swap = re-project) |
| `dim` | `int` NOT NULL | vector dimension |
| `embedding` | `vector(dim)` (pgvector) | the vector; HNSW index for ANN search |
| `embedded_at` | `timestamptz` | staleness / rebuild bookkeeping |

Rebuildable from `memory` at any time; losing it is a re-index, not data loss.

---

## 6. `consolidation_edge` — cite-don't-replace (C7)

| Column | Type | Why |
| :-- | :-- | :-- |
| `consolidated_id` | `uuid` FK→memory | the summary/rollup memory |
| `source_id` | `uuid` FK→memory | a memory it cites |
| `created_at` | `timestamptz` | |

Consolidation produces a new memory linked to its sources; sources remain retrievable. This is the
structural guard against the Approach-C failures (F5 loss, F6 drift).

---

## 7. `access_log` — audit (C8, C9)

| Column | Type | Why |
| :-- | :-- | :-- |
| `id` | `uuid` PK | |
| `request_id` | `uuid` NOT NULL | joins to the decision trace (C9) |
| `tenant_id` | `uuid` NOT NULL | who the read was scoped to |
| `user_id` | `uuid` | actor |
| `returned_memory_ids` | `uuid[]` | exactly what was injected |
| `occurred_at` | `timestamptz` NOT NULL | |

Every retrieval writes one row. Enables the P5/P7 requirement: reconstruct who saw what, and confirm
no cross-tenant read ever occurred.

---

## 8. `deletion_request` — erasure + the F9 window (C7)

| Column | Type | Why |
| :-- | :-- | :-- |
| `id` | `uuid` PK | |
| `tenant_id` | `uuid` NOT NULL | |
| `scope` | `deletion_scope` enum | `subject \| account \| user \| tenant` |
| `target_ref` | `text` NOT NULL | what to erase (e.g. a data-subject id) |
| `requested_at` | `timestamptz` NOT NULL | window start |
| `completed_at` | `timestamptz` NULL | window end; `completed_at - requested_at` **is** the measured F9 window |
| `status` | enum | `pending \| completed \| failed` |

Because `memory_embedding` cascades on `memory` delete ([[ADR-005]]), completion is typically within a
single transaction; this table exists to *measure and prove* the window, not merely to hope for it.

---

## 9. What is deliberately NOT modelled in v1 (traceable non-goals)
- **Raw transcripts** — referenced via `memory_source`, owned by a separate conversation store
  (different freshness/ownership — D1 non-goal).
- **Learned ranking weights** — ranking signals are hand-specified (D1 non-goal); no weights table.
- **Team-shared memory** — `user_id` NULL is reserved for it but consent/access rules are unresolved
  (P5/P6) and deferred.
- **Regional partitioning** — single region ([[ADR-004]]); residency is an `account_attribute`/
  `requirement` fact in v1, not an infra boundary.
