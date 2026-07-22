# Week 1 — Component Scan

**Deliverable 2, Week 1** · Conversational Memory Intelligence System · Dheeraj Pranav · 22 July 2026

Follows the handbook Appendix B scan template and §4.2 process. The week's target (step 1) is the
four components flagged weakest/least-certain in `../research_landscape.md §1`:
**admission (C2)**, **ranking/temporal validity (C5)**, **lifecycle/consolidation (C7)**, and
**evaluation (C10)**. Other components were glimpsed to confirm no higher-priority gap opened.

Tags: `verified` (in the source) · `inference` (my reading) · `assumption` · `to measure`.

---

## Week and current design gaps

Entering Week 1, the design (from Deliverable 1) is a first-principles specification with **zero
measured numbers** and four soft spots:

- **G1 — admission mechanism is under-specified.** D1 says admission decides store/update/discard
  but not *how* the update-vs-add call is made or how PII is gated concretely.
- **G2 — temporal validity is asserted, not evidenced.** `first_principles §6` falsifier 1 makes
  the entire justification for multi-signal ranking (C5) hinge on whether a superseded fact really
  outranks the current one. Needs both external evidence and a Day-3 measurement.
- **G3 — consolidation is the highest-risk component (F5/F6) and has no chosen mechanism.**
- **G4 — no evaluation set exists.** C10 is a non-negotiable gate (baseline comparison) and a real
  build cost, not merely a policy statement.

---

## Component scan

For each component: **sources glimpsed/read**, **mechanisms found**, **relevance to the current
system** (which capability / failure mode / gap).

### A. Extraction & admission — C1, C2 · gap G1
- **Sources:** Mem0 (2504.19413) **read**; Presidio (github) **read**; Generative Agents (write path) prior.
- **Mechanisms found:**
  - `verified` Mem0 splits admission into *extraction* (LLM pulls candidate facts from the last
    turns + a rolling summary) and an *update phase* where an LLM chooses ADD / UPDATE / DELETE /
    NOOP by comparing each candidate to the top-k semantically similar existing memories.
  - `verified` Presidio provides deterministic PII recognizers (regex + NER + checksum validators,
    e.g. for cards/emails/phones) with confidence scores and an anonymizer step.
- **Relevance:** Mem0's operation-selector is a concrete realisation of C2's "typed outcome:
  store / update / discard" and its UPDATE path partially serves C7. Presidio is a testable PII
  gate for C2/C8 against F11 — and testability matters because D6 requires positive+negative PII
  cases. `inference` Mem0's LLM-per-candidate cost is the thing to watch against our ≤15% cost
  constraint; its own numbers (>90% token savings vs *full context*) are not a like-for-like
  comparison with *our* naive RAG baseline, so they don't transfer directly. `to measure`.

### B. Memory model & representation — C3 · gap G2
- **Sources:** Zep/Graphiti (2501.13956) **read**; Memory Networks/NTM prior.
- **Mechanisms found:**
  - `verified` Bi-temporal edges: *valid-from / valid-to* (world time) separate from *created-at /
    expired-at* (system time). A new contradicting fact **invalidates** the old edge (sets its
    valid-to / expired-at) rather than deleting it, preserving history.
- **Relevance:** this is the strongest external evidence for the D1 claim (P4 → C3) that a memory
  is "a proposition + a time interval + a supersession relation." `inference` The important
  transfer is the *bi-temporal data model and invalidation semantics*, not Graphiti's full graph
  engine — adopting the whole KG would violate the v1 non-goal of hand-specified, inspectable
  structure and add a large operational surface.

### C. Ranking & conflict resolution — C5 · gap G2
- **Sources:** Generative Agents (relevance+recency+importance) prior; Zep (invalidation) **read**.
- **Mechanisms found:** `verified` Generative Agents' linear combination of three signals is the
  baseline for multi-signal ranking; `verified` Zep resolves conflict *structurally* (invalidate
  the superseded edge) so the ranker never has to choose between two live contradictory facts.
- **Relevance:** suggests a division of labour — **conflict resolution belongs upstream** (in
  representation/lifecycle, via validity + invalidation) so that **ranking** only orders facts that
  are all currently valid. `inference` This is cleaner than asking a relevance+recency score to
  encode validity, which `failure_analysis D-1` already argued it structurally cannot.

### D. Reflection & lifecycle — C7 · gap G3
- **Sources:** A-MEM (2502.12110) **read**; Generative Agents (reflection) prior; MemGPT prior.
- **Mechanisms found:** `verified` A-MEM generates rich notes and links related notes; its "memory
  evolution" lets a new note rewrite the tags/context of older notes.
- **Relevance:** `inference` A-MEM is a direct cautionary case. Its evolution step *replaces* prior
  content, which is exactly the C7 invariant violation ("consolidate with citation, never replace")
  that D1 derived from Approach C's F5/F6 failures. It is evidence for *what not to do*, which is as
  useful as a positive result. The linking idea (episodic → semantic association) is a `defer`
  candidate for a later week once the core lifecycle is measured.

### E. Evaluation & observability — C9, C10 · gap G4
- **Sources:** LongMemEval (2410.10813) **read**; LOCOMO **glimpsed**.
- **Mechanisms found:** `verified` LongMemEval's five-ability taxonomy and its indexing/retrieval/
  reading decomposition; its explicit **knowledge-updates** and **abstention** task types.
- **Relevance:** high. `inference` Its knowledge-updates ability is F4 (superseded fact) and its
  abstention ability is the cold-start/no-relevant case from D1 — so its task taxonomy is a
  ready scaffold for our C10 adversarial set. What it does **not** cover is GTM-specific:
  cross-tenant near-duplicates (F10) and incidental PII (F11). Those we must author ourselves.

### F. Components glimpsed, no new priority gap
- **Context construction (C6):** LLMLingua (2310.05736) **glimpsed** — compression is interesting
  but our budget is already small (≤2k tokens) and facts are compact, so payoff looks marginal.
  No gap escalation.
- **Index & storage (C4/C8):** per-tenant namespace/partition isolation is standard practice;
  confirms C8 is an engineering pattern, not a research risk. No gap escalation.
- **Privacy/unlearning (C7/C8):** SISA/machine-unlearning (1912.03817) **glimpsed** — targets model
  retraining, not datastore deletion; `inference` analogy does not transfer, noted to avoid
  over-applying it.

---

## Candidate backlog produced this week

Raw candidates before shortlisting (shortlist + full evaluation in `idea_evaluation_matrix.md`):

| # | Candidate | Component | Capability | Failure | First-look |
| :-- | :-- | :-- | :-- | :-- | :-- |
| c1 | Bi-temporal validity + supersession-by-invalidation (Zep) | representation | C3, C5, C7 | F4 | strong |
| c2 | LongMemEval task taxonomy as C10 eval scaffold | evaluation | C10 | F4, cold-start | strong |
| c3 | Mem0 ADD/UPDATE/DELETE/NOOP operation selector | admission | C2, C7 | F8 | promising, cost risk |
| c4 | Presidio PII gate at admission | admission | C2, C8 | F11 | strong, low-risk |
| c5 | A-MEM memory evolution (link + rewrite old notes) | lifecycle | C7 | F5, F6 | cautionary (conflicts w/ invariant) |
| c6 | LLMLingua injection compression | context | C6 | F2 | marginal at our budget |
| c7 | "Back to Basics" minimalist retrieval (challenge) | whole design | — | — | handled in challenge_notes |

---

## Self-explanation (handbook §4.2, principle 3)

- **Why these four target components and not the glamorous ones (reflection/agentic autonomy)?**
  Because `first_principles §5` says temporal validity does more work than reflection, and because
  the two non-negotiable gates I can already see (baseline comparison, isolation/deletion) route
  through evaluation and admission. Effort follows leverage and risk, not novelty.
- **What would make me wrong about the target?** If Day-3 shows the naive baseline already handles
  superseded facts well, G2 collapses and next week's attention shifts to admission precision (G1)
  instead. That is falsifier 1 from `first_principles §6`, and Week 1 is deliberately set up to
  feed it.
