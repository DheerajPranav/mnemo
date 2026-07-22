# Design Backlog — Conversational Memory Intelligence System

Durable, append-only backlog of ideas surfaced by the weekly research scans (handbook §4.2 step 9).
Each row carries its disposition and a pointer to where it was evaluated. Rows never get deleted;
they get their status updated (with a date) so the reasoning history survives.

**Author:** Dheeraj Pranav · **Last updated:** 22 July 2026 (Week 1)

Status vocabulary (handbook §4.2 step 7): **ADOPT** · **PROTOTYPE** · **DEFER** · **REJECT**.
A `to measure` note marks items whose disposition is provisional on a Deliverable 3 number.

---

## Active (adopt / prototype)

| ID | Idea | Capability · Failure | Status | Provenance | Next action |
| :-- | :-- | :-- | :-- | :-- | :-- |
| B-001 | Bi-temporal validity + supersession-by-invalidation (representation only, not the KG engine) | C3, C5, C7 · F4 | **ADOPT** `to measure` | Zep 2501.13956 · Week 1 · ADR-001 | D3 3-arm comparison (naive / +recency / validity-filter) |
| B-002 | LongMemEval ability taxonomy as C10 eval scaffold, extended with GTM cases | C10 · F4, cold-start, F10, F11 | **ADOPT** | LongMemEval 2410.10813 · Week 1 · ADR-002 | Build the fixed adversarial set for D3 on this scaffold |
| B-003 | Presidio PII gate at admission (deterministic recognizers first, NER optional) | C2, C8 · F11 | **ADOPT** | Presidio (OSS) · Week 1 · ADR-003 | Wire into admission stage in D6; labelled pos/neg PII set |
| B-004 | Mem0-style ADD/UPDATE/DELETE/NOOP operation selector | C2, C7 · F8 | **PROTOTYPE** | Mem0 2504.19413 · Week 1 | D3: measure write-path cost vs *our* baseline, update accuracy |
| B-005 | Relocate conflict resolution off the ranker into the write path (consequence of B-001) | C5, C7 · F4 | **ADOPT** | Week 1 derivation · ADR-001 | Reflect in D4 architecture: ranker orders only currently-valid facts |

## Deferred

| ID | Idea | Capability | Status | Provenance | Revisit when |
| :-- | :-- | :-- | :-- | :-- | :-- |
| B-006 | A-MEM note-linking (episodic→semantic association) — **link idea only** | C7 | **DEFER** | A-MEM 2502.12110 · Week 1 | after citation-preserving consolidation is measured |
| B-007 | Turn-Isolation Retrieval as a stronger baseline retriever | C6 (baseline) | **DEFER** (into D3 protocol) | Back to Basics 2604.11628 · Week 1 | D3 baseline design — use to avoid a straw-man baseline |
| B-008 | Cross-encoder reranking of retrieved facts | C5 | **DEFER** | industry practice · Week 1 glimpse | once multi-signal ranking is measured and shown insufficient |

## Rejected

| ID | Idea | Status | Provenance | Reason · revisit condition |
| :-- | :-- | :-- | :-- | :-- |
| B-009 | A-MEM "memory evolution" (rewrite/mutate older notes) | **REJECT** | A-MEM 2502.12110 · Week 1 | Violates C7 "consolidate with citation, never replace" → reintroduces F5/F6. Revisit only if an append-only, provenance-preserving variant exists. |
| B-010 | LLMLingua injection compression | **REJECT** (v1) | LLMLingua 2310.05736 · Week 1 | Marginal at ≤2k-token budget over compact typed facts; adds a model call. Revisit if budget shrinks or free-text memories are admitted. |
| B-011 | SISA / machine-unlearning for deletion | **REJECT** | Bourtoule 1912.03817 · Week 1 | Targets *model* retraining; our deletion is a datastore+index op. Analogy does not transfer. |

## Open (needs external evidence — no source yet)

| ID | Question | Capability | Note |
| :-- | :-- | :-- | :-- |
| B-012 | Is there *any* published work that demands decision-observability (C9) as a requirement? | C9 | C9 rests only on premise P7; no cited source forces it. Watch eval/tracing literature. |
| B-013 | Automatic supersession vs. inject-both-with-dates (open question 2 from D1) | C5, C7 | Irreversible write vs. deferring resolution to the model. Settle empirically. |

---

## Rollup for Deliverable 4 (design) and Deliverable 3 (baseline)

- **Into D4 design now (adopted):** B-001 bi-temporal schema, B-005 conflict-resolution relocation,
  B-002 eval taxonomy, B-003 admission PII gate. Each has an ADR in `../design/decision_records/`.
- **Into D3 baseline protocol:** B-007 (fair strong baseline), B-004 (prototype cost measurement),
  and the 3-arm comparison for B-001. These are why the D3 protocol is shaped the way it is.
