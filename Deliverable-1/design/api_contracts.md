# API Contracts — Conversational Memory Intelligence System (v1)

**Deliverable:** 4 (System Design) · **Author:** Dheeraj Pranav · **Date:** 2026-07-22
**Traces to:** C1–C10 · **Data model:** [[data_model]] · **Isolation:** [[ADR-005]]

Internal service contracts for the memory subsystem, called by the GTM agent. Two synchronous paths
(admit on write, retrieve on read) plus lifecycle, deletion, observability, and eval entrypoints.

## Cross-cutting invariants (apply to every endpoint)

1. **Tenant is ambient, never a parameter.** `tenant_id` comes from the authenticated call context and
   is bound to the DB session (RLS GUC) and the repository constructor. **No request body carries a
   `tenant_id` field** — there is no wire to spoof (C8/F10, [[ADR-005]]). Passing one is a 400.
2. **Every call returns a `trace_id`.** The full decision trace is retrievable (C9). No silent stages.
3. **PII never crosses on the output path.** If content was blocked at admission it was never stored;
   there is nothing to redact downstream (C2/F11, [[ADR-003]]).
4. **Reads see only currently-valid facts.** `status='current' AND valid_to IS NULL` is enforced in the
   repository, not left to callers (F4, [[ADR-001]]).

---

## 1. `POST /memory/admit` — write path (C1, C2, C3, C7)

Extract candidate claims from conversation turns, screen, and decide store / update / discard.

**Request**
```json
{
  "account_id": "uuid",
  "user_id": "uuid",
  "session_id": "uuid",
  "turns": [
    {"turn_id": "uuid", "role": "user|assistant", "text": "string", "observed_at": "ts"}
  ]
}
```

**Pipeline (each numbered stage emits a trace event):**
1. **Extract** (LLM) — turns → candidate typed claims `{type, subject, content, confidence, observed_at}`.
2. **PII gate** (Presidio, deterministic-first) — reject/redact ineligible content **before** storage.
   Blocked candidates never reach the store; they appear in the response as `pii_blocked` with the
   recognizer that fired, not their content.
3. **Op-select** (Mem0-style, prototype) — per surviving candidate decide `store | update | discard`
   against existing current facts on `(account_id, subject)`; dedup near-identical (F8).
4. **Commit** — `store` inserts a `current` fact; `update` runs the supersession transaction
   (invalidate prior, insert new — [[ADR-001]]); `discard` is logged, not stored.

**Response**
```json
{
  "trace_id": "uuid",
  "admitted":   [{"memory_id": "uuid", "type": "...", "subject": "...", "op": "store"}],
  "updated":    [{"memory_id": "uuid", "supersedes": "uuid", "subject": "..."}],
  "discarded":  [{"reason": "duplicate|low_salience", "subject": "..."}],
  "pii_blocked":[{"recognizer": "PHONE_NUMBER|MEDICAL|...", "action": "blocked|redacted"}]
}
```
**Errors:** `400` malformed / contains `tenant_id`; `422` extraction produced no typed claim;
`503` extractor/embedder unavailable (candidates are queued, not dropped — admission must not lose a
correction, C1).

---

## 2. `POST /memory/retrieve` — read path (C5, C6, C8)

Return the budgeted, ordered memory set to inject — or abstain.

**Request**
```json
{
  "account_id": "uuid",
  "user_id": "uuid",
  "query": "string",
  "token_budget": 2000,
  "k": 12
}
```
`k` is the candidate pool before budgeting (default 12); `token_budget` defaults to 2000 ([[ADR-004]]).

**Pipeline:**
1. **Candidate retrieval** — tenant+account-scoped ANN over `memory_embedding`, currently-valid only,
   top-`k`. Isolation enforced below this call (C8).
2. **Multi-signal rank** (C5) — score = weighted(relevance, recency, importance-by-type, confidence).
   Hand-specified weights (D1 non-goal: inspectable). Conflict already resolved at write time.
3. **Budgeted construction** (C6) — add memories in rank order until `token_budget` binds; **position-
   aware** ordering (highest-value at the ends, not the middle — P2/F3). If the top score is below the
   **abstention floor**, return `abstained: true` with an empty set (the cold-start fix, D3).

**Response**
```json
{
  "trace_id": "uuid",
  "abstained": false,
  "injected": [
    {"memory_id": "uuid", "type": "...", "subject": "...", "content": "...",
     "score": 0.0, "signals": {"relevance": 0.0, "recency": 0.0, "importance": 0.0, "confidence": 0.0},
     "est_tokens": 0}
  ],
  "dropped_for_budget": ["uuid"],
  "used_tokens": 0
}
```
Every returned set is also written to `access_log` (C8/C9). **Errors:** `400` if `tenant_id` present.

---

## 3. Lifecycle (C7)

| Endpoint | Purpose | Notes |
| :-- | :-- | :-- |
| `POST /memory/{id}/correct` | user-driven correction | confidence 1.0; runs the supersession txn (C1/F1) |
| `POST /jobs/consolidate` | periodic rollup | creates a cited summary memory; **never deletes sources** (C7, avoids F5/F6) |
| `POST /jobs/decay` | age out low-salience unused memories | sets `status`, keeps row for audit |
| `POST /jobs/expire` | validity-end / commitment-due sweep | sets `valid_to`, `status='expired'` |

## 4. `POST /deletion` — erasure (C7, F9)

**Request** `{"scope": "subject|account|user|tenant", "target_ref": "string"}`
**Behaviour:** creates a `deletion_request`; deletes matching `memory` rows, cascading
`memory_embedding` in the **same transaction** ([[ADR-005]]); sets `completed_at`. Returns
`{"deletion_request_id": "uuid", "deleted_count": n, "window_ms": n}`.
The `window_ms` is the measured F9 consistency window — the guarantee is *reported*, not assumed.

## 5. `GET /trace/{trace_id}` — observability (C9)

Returns the structured decision trace for any admit/retrieve: candidates considered, per-signal scores,
budget-driven drops, policy suppressions (PII), and the final set. This is the artifact that lets D3's
failure taxonomy be populated from **real** traffic, not just the fixed set (P7).

## 6. `POST /eval/run` — offline evaluation (C10)

Runs the versioned fixed set (D3 dataset + LongMemEval scaffold, [[ADR-002]]) through the **3 arms**
(naive / +recency / validity-filter) and reports component + end-to-end metrics against the D3 baseline.
Reproducible; no live traffic. This is the non-negotiable baseline-comparison gate.

---

## 7. Acceptance tests (each contract ships with these — feeds D6)
- **Isolation:** a retrieve for tenant A never returns tenant B rows, incl. when the raw predicate is
  omitted (RLS must block) and when a mis-scoped repository is attempted (must not compile/construct).
- **Supersession:** after `correct`, retrieve returns only the new fact; the old is `superseded`, still
  in the store, never injected (F4).
- **PII:** an admit containing a phone/medical token stores nothing for that candidate; `retrieve` can
  never surface it (F11).
- **Abstention:** a query with no valid memory returns `abstained: true`, empty set (cold-start).
- **Budget:** `used_tokens ≤ token_budget`; dropped memories are the lowest-ranked (C6).
- **Deletion:** post-`/deletion`, the target is unretrievable within `window_ms ≤` the ADR-004 guarantee.
