# Research Landscape — Conversational Memory Intelligence System

**Purpose.** The maintained map (handbook §2.3) of the memory-system research space, organised by
the component it could improve and tied to this project's derived capabilities C1–C10
(`../reconstruction/first_principles.md`) and failure modes F1–F11
(`../reconstruction/failure_analysis.md`). Updated each week; the per-week *scan* lives in
`week-N/`, this file is the durable index.

**Author:** Dheeraj Pranav · **Last updated:** 22 July 2026 (Week 1)

**Evidence tags** (same scheme as Deliverable 1): `verified` = stated in the cited source ·
`inference` = my reading · `assumption` = working assumption · `to measure` = pending a
Deliverable 3 number.

> **Reading discipline (handbook §2.2).** Nothing in this file is adopted from an abstract or a
> secondary summary. Shortlisted items get targeted validation against the primary source before
> any design change. Where I have only glimpsed (title/abstract/README/results) and not yet read
> the method, the row says **glimpsed**; where I have read the mechanism, it says **read**.

---

## 1. How this maps to the design

The design is a pipeline of five decisions (admission → representation → retrieval/ranking →
injection → lifecycle) over two invariants (isolation, observability). Each handbook component
below is annotated with the capability it serves and the current design stance, so a new idea can
be judged by whether it improves a *named* capability against a *named* failure.

| Handbook component | Serves | Current stance (v1, from D1) | Weakest / least certain? |
| :-- | :-- | :-- | :-- |
| Memory model & representation | C3 | Typed, resolved facts w/ provenance, confidence, **validity interval** — not raw chunks | — |
| Attention & context | C6 | Budgeted construction, explicit ordering; long-context is *not* a substitute | — |
| Extraction & admission | C1, C2 | Admission gate: extract → type → salience → PII gate; not blanket capture | **yes** (OQ-1: typed extraction may trade F7 for a worse failure) |
| Retrieval augmentation | C4, C5 | Source-of-truth store + rebuildable index; hybrid retrieval TBD | — |
| Index & storage | C4, C8 | Index = derived projection; tenant partitioning at index level | — |
| Ranking & conflict resolution | C5 | Multi-signal (relevance, recency, importance, confidence) + supersession | **yes** (C5 "does the most work", `first_principles §5`) |
| Context construction | C6 | Token budget ≤2k/16k, ordering matters (Lost-in-the-Middle) | — |
| Reflection & lifecycle | C7 | Update, consolidate **with citation**, decay, expire, delete | **yes** (F5/F6 over-determined, highest-risk component) |
| Evaluation & observability | C9, C10 | Structured per-request trace; fixed offline adversarial eval set vs baseline | **yes** (no eval set exists yet; C10 is a build cost, not just a policy) |
| Privacy, safety, isolation | C2, C7, C8 | PII gate at admission; isolation as invariant; deletion w/ tested window | — |

The four "weakest" rows are where Week 1 spends its attention (handbook §4.2 step 1).

---

## 2. Component map with tracked work

Starting sources are handbook Appendix G. **Tracked (recent)** lists work published *after* the
handbook (June 2026) or otherwise not in Appendix G that bears on a named capability — the
handbook explicitly asks for this (§2.3).

### 2.1 Extraction & admission — C1, C2 (F8, F11)
- **Starting:** conversational-memory & information-extraction literature; Generative Agents (write path).
- **Tracked:**
  - `verified` **Mem0** (arXiv:2504.19413) — LLM extracts candidate facts, then an operation
    selector emits ADD / UPDATE / DELETE / NOOP against existing memory. Reports 91% lower p95
    latency and >90% token-cost savings vs full-context on LOCOMO. **read** (method + results).
  - `verified` **Microsoft Presidio** (github.com/microsoft/presidio) — analyzer + anonymizer for
    PII detection/redaction; deterministic, extensible recognizers. Candidate for the admission
    PII gate. **read** (docs).
- **Gap it exposes:** the current design specifies *that* admission decides store/update/discard
  but not *how* the update-vs-add decision is made. Mem0 supplies a concrete mechanism.

### 2.2 Memory model & representation — C3 (F4, F5, F7)
- **Starting:** Memory Networks; NTM; End-to-End Memory Networks (read/write/address decomposition).
- **Tracked:**
  - `verified` **Zep / Graphiti** (arXiv:2501.13956) — temporal knowledge graph with a
    **bi-temporal** model: each edge carries *valid* time (when the fact holds in the world) and
    *transaction* time (when the system learned it); contradicting edges are **invalidated**, not
    deleted. Directly implements validity interval + supersession. **read** (method + results).
- **Gap it exposes:** validates that temporal validity belongs *in the representation*, not in a
  ranking heuristic. Confirms the D1 design instinct with external evidence.

### 2.3 Ranking & conflict resolution — C5 (F4, F8)
- **Starting:** Generative Agents (relevance+recency+importance); learning-to-rank.
- **Tracked:** Zep (above) for conflict resolution via edge invalidation; reranking practice
  (cross-encoder rerankers) as a `defer` candidate for later weeks.
- **Note:** `first_principles §5` flags C5 as the component doing the most work; it gets the
  earliest adversarial testing in D3.

### 2.4 Reflection & lifecycle — C7 (F1, F5, F6, F9)
- **Starting:** Generative Agents (reflection); MemGPT (paging); continual-learning/forgetting.
- **Tracked:**
  - `verified` **A-MEM** (arXiv:2502.12110) — Zettelkasten-style notes with keywords/tags,
    LLM-decided links between notes, and **memory evolution** (a new note can update the
    attributes of older notes). **read** (method).
  - `inference` A-MEM's "memory evolution" *mutates* prior notes — which is exactly the F6 drift
    / F5 loss risk the design's "consolidate with citation, never replace" invariant exists to
    prevent. Tracked as a cautionary contrast, not a candidate to adopt wholesale.

### 2.5 Context construction — C6 (F2, F3)
- **Starting:** MemGPT; RAG + long-context.
- **Tracked:** `verified` **LLMLingua** (arXiv:2310.05736) — prompt compression via a small LM to
  drop low-information tokens. Candidate for squeezing the injection budget. **glimpsed**.

### 2.6 Evaluation & observability — C9, C10
- **Starting:** RAG/agent evaluation & retrieval benchmarking.
- **Tracked:**
  - `verified` **LongMemEval** (arXiv:2410.10813, ICLR 2025) — 500 curated QAs over scalable
    chat histories testing five abilities: information extraction, multi-session reasoning,
    **temporal reasoning**, **knowledge updates**, and **abstention**. Reports ~30% accuracy drop
    for commercial assistants on sustained interaction. Decomposes memory into indexing / retrieval
    / reading. **read** (task design + framework).
  - `verified` **LOCOMO** — long-conversation memory benchmark used by Mem0's evaluation. **glimpsed**.
- **Gap it exposes:** the two abilities LongMemEval names as hardest (knowledge updates, abstention)
  are exactly F4 (superseded fact) and the cold-start/no-relevant case. This is a ready-made
  scaffold for the C10 eval set instead of inventing task types from scratch.

### 2.7 Privacy, safety, isolation — C2, C7, C8 (F9, F10, F11)
- **Starting:** privacy-preserving retrieval; machine unlearning; access-control; multi-tenant systems.
- **Tracked:**
  - `verified` **Machine Unlearning / SISA** (Bourtoule et al., arXiv:1912.03817) — relevant to
    *model* forgetting; `inference` less relevant here because our deletion is a datastore + index
    operation, not a retraining problem. Noted so the analogy is not over-applied.
  - Multi-tenant vector-DB isolation via per-tenant namespaces/partitions (industry practice) —
    the concrete form of C8's "isolation as an invariant." **glimpsed**.

### 2.8 Challenge / counter-evidence (tracked deliberately)
- `verified` **"Back to Basics: Let Conversational Agents Remember with Just Retrieval and
  Generation"** (arXiv:2604.11628, 2026) — argues the bottleneck is a *Signal Sparsity Effect*,
  not memory architecture, and that a minimalist retrieval+generation method (Turn-Isolation
  Retrieval + Query-Driven Pruning) beats stronger memory baselines on token/latency efficiency.
  **read** (abstract + claims). Tracked because a good research process seeks the strongest
  argument *against* building the system; handled in `week-1/challenge_notes.md`.

---

## 3. Standing questions this landscape must keep answering

1. Which recent result, if it replicated in the GTM setting, would most change the design? *(Week 1
   answer: Zep's temporal model — but it mostly confirms rather than overturns.)*
2. What is the strongest published argument that this whole system is over-engineered? *(Week 1
   answer: "Back to Basics" — addressed, does not refute the isolation/deletion/PII requirements.)*
3. Which capability still has *no* external evidence and rests only on first principles? *(C9
   observability — no cited source demands it; it comes from premise P7 alone. Watch for eval /
   tracing work that would corroborate or challenge it.)*

---

## 4. Sources (Week 1)

1. Rasmussen, P., Paliychuk, et al. *Zep: A Temporal Knowledge Graph Architecture for Agent Memory.* 2025. arXiv:2501.13956
2. *Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory.* 2025. arXiv:2504.19413
3. Xu, W., Liang, Z., Mei, K., et al. *A-MEM: Agentic Memory for LLM Agents.* 2025. arXiv:2502.12110
4. Wu, D., et al. *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory.* ICLR 2025. arXiv:2410.10813
5. Wu, Y., Chen, W., et al. *Back to Basics: Let Conversational Agents Remember with Just Retrieval and Generation.* 2026. arXiv:2604.11628
6. Jiang, H., et al. *LLMLingua: Compressing Prompts for Accelerated Inference of LLMs.* 2023. arXiv:2310.05736
7. Bourtoule, L., et al. *Machine Unlearning.* 2019. arXiv:1912.03817
8. Microsoft Presidio — https://github.com/microsoft/presidio
9. Plus handbook Appendix G foundational set (carried from Deliverable 1).

**AI assistance disclosure.** Claude helped locate and summarise candidate sources and draft this
map. Primary-source reading, the relevance judgments, and every adopt/prototype/defer/reject call
are mine (Dheeraj) and are recorded with their evidence in `week-1/`.
