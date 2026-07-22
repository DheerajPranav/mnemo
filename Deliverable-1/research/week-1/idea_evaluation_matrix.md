# Week 1 — Idea Evaluation Matrix

**Deliverable 2, Week 1** · Dheeraj Pranav · 22 July 2026

Shortlist from `component_scan.md`, each idea evaluated against the current design and closed with
an explicit **adopt / prototype / defer / reject** (handbook §4.2 steps 5–7). Cost/latency/
complexity/security columns are the §4.3 review probes made concrete.

Scoring key: L / M / H = low / medium / high. "Benefit" is expected benefit to a *named*
capability; "Risk" folds latency + complexity + security. Decisions are justified per-idea below.

| # | Idea | Component · Capability · Failure | Evidence strength | Integration cost | Added latency | Complexity | Security/privacy effect | Benefit | **Decision** |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| I1 | Bi-temporal validity + supersession-by-invalidation | representation · C3,C5,C7 · **F4** | `verified` Zep: +up to 18.5% LongMemEval, DMR 94.8% vs 93.4% | M (schema + write-path invalidation) | L (a field compare, no model call) | M | Neutral/positive (history preserved for audit) | **H** — fixes the failure that justifies C5 | **ADOPT** (model only, not the KG engine) |
| I2 | LongMemEval taxonomy as C10 eval scaffold | evaluation · C10 · F4, cold-start | `verified` public benchmark, ICLR'25, 500 QAs | L (adapt task types) | n/a (offline) | L | Positive (abstention tests reduce over-answering) | **H** — de-risks the whole measurement chain | **ADOPT** (taxonomy + subset; extend for GTM) |
| I3 | Presidio PII gate at admission | admission · C2,C8 · **F11** | `verified` mature OSS, deterministic recognizers | L–M (one library, recognizer config) | L (regex/NER, no LLM needed) | L | **Strongly positive** (testable pos/neg PII cases) | H — turns F11 from policy into tested control | **ADOPT** |
| I4 | Mem0 ADD/UPDATE/DELETE/NOOP operation selector | admission · C2,C7 · F8 | `verified` 91% lower p95 lat, >90% token save vs *full-context* | M (LLM call + prompt design) | **M–H** (LLM per candidate) | M | Neutral | M–H — concrete update-vs-add mechanism | **PROTOTYPE** (measure cost in D3) |
| I5 | A-MEM memory evolution (rewrite old notes) | lifecycle · C7 · F5,F6 | `verified` beats SOTA on 6 models — but in a no-regulation setting | M | M (LLM linking) | H | **Negative** (mutation loses provenance) | Low here — conflicts w/ C7 invariant | **DEFER** (revisit link idea only) |
| I6 | LLMLingua injection compression | context · C6 · F2 | `verified` strong compression ratios on long prompts | M | M (compressor model call) | M | Neutral | Low at our ≤2k budget | **REJECT** (v1; revisit if budget grows) |

---

## Per-idea justification

### I1 — Bi-temporal validity + supersession-by-invalidation · **ADOPT (representation only)**
- **Problem addressed:** F4, a superseded fact served as current — the failure that
  `first_principles §6` falsifier 1 says the *entire* case for multi-signal ranking depends on.
- **Mechanism:** store on each typed fact a *valid-from / valid-to* (world time) and *recorded-at /
  invalidated-at* (system time); when a new fact contradicts an existing one, set the old fact's
  `valid-to` and `invalidated-at` instead of deleting it. Retrieval filters to currently-valid
  facts; history remains for audit and for re-derivation.
- **Evidence (`verified`):** Zep reports up to +18.5% on LongMemEval and 94.8% vs 93.4% on DMR
  against MemGPT, attributing gains substantially to temporal handling.
- **Assumptions that must hold (`assumption`):** (a) contradiction is detectable at admission with
  acceptable precision; (b) most facts have a resolvable subject key to compare against. Both are
  `to measure` in D3/D6.
- **Current approach → proposed change:** D1 already specifies a validity interval abstractly;
  this *pins the concrete bi-temporal schema and invalidation rule*, and — the real design move —
  **relocates conflict resolution out of the ranker into the write path**, so ranking only ever
  orders currently-valid facts.
- **Why adopt the model but not Graphiti:** the full temporal KG engine violates the v1 non-goal of
  hand-specified inspectable structure and adds heavy operational surface; the bi-temporal *fields*
  and *invalidation semantics* capture the benefit at a fraction of the cost. `inference`
- **Validation (D3, bounded):** measure how often a superseded preference outranks the current one
  under the naive single-signal baseline (establish the failure rate); success criterion for the
  eventual fix = validity-filtered retrieval reduces that rate to ~0 on the fixed set.
- **Falsifier:** if D3's baseline already resolves supersession from recency alone at a comparable
  rate, I1's benefit is not real and it is downgraded to `defer`.

### I2 — LongMemEval taxonomy as the C10 eval scaffold · **ADOPT (taxonomy + subset, extend)**
- **Problem addressed:** G4 — no evaluation set exists, and baseline comparison is a non-negotiable
  gate. Building task types from scratch is the expensive, error-prone path.
- **Mechanism:** reuse LongMemEval's five-ability decomposition and its knowledge-update /
  abstention case *designs* as the backbone of our fixed adversarial set; author GTM-specific cases
  it lacks (cross-tenant near-duplicate F10, incidental PII F11) on top.
- **Evidence (`verified`):** public ICLR'25 benchmark, 500 curated QAs, reports ~30% accuracy drop
  for commercial assistants — evidence the task types are genuinely hard.
- **Integration cost:** L. It is a design scaffold, not a dependency; we do not need to run their
  full harness, only adopt their taxonomy and a subset of case patterns.
- **Validation:** the eval set is usable if, on the naive baseline, each ability's cases produce a
  *measurable spread* (some pass, some fail) rather than all-pass or all-fail — a saturated set
  measures nothing. `to measure` in D3.

### I3 — Presidio PII gate at admission · **ADOPT**
- **Problem addressed:** F11 — sensitive data admitted by default; `failure_analysis D-6` argues
  PII must be caught at admission, never as an output filter.
- **Mechanism:** run Presidio recognizers over each admission candidate; block/flag/redact
  configured PII categories before anything is written to the store or index.
- **Why adopt now:** it is deterministic and testable, which is exactly what the D6 gate needs
  (positive + negative PII cases). It removes an LLM from the critical PII path (lower cost/latency
  and no prompt-injection surface on that path).
- **Limitation (`inference`):** recognizer recall is imperfect; residual PII is possible, so the
  design keeps deletion (C7) as the backstop. Adoption is "gate + backstop," not "gate alone."
- **Validation:** precision/recall of the gate on a labelled PII case set; `to measure` in D6.

### I4 — Mem0 operation selector (ADD/UPDATE/DELETE/NOOP) · **PROTOTYPE**
- **Problem addressed:** the mechanism gap in C2/C7 — how the update-vs-add decision is actually
  made.
- **Why prototype, not adopt:** it puts an LLM call on the write path for every candidate. Mem0's
  headline savings are measured against *full-context prompting*, not against *our* naive RAG
  baseline, so they do not transfer as a cost argument here. The honest move is a bounded
  experiment. `inference`
- **Validation (D3):** measure added tokens/latency per admitted candidate and the update-decision
  accuracy on the fixed set; **reject criterion** = write-path cost pushes the memory subsystem
  over the ≤15% per-turn cost envelope without a matching quality gain.

### I5 — A-MEM memory evolution · **DEFER**
- **Why not adopt:** its evolution step rewrites older notes' content, which violates the C7
  invariant "consolidate with citation, never replace" that D1 derived precisely to avoid F5/F6.
  Adopting it would reintroduce the failure the design exists to prevent.
- **What is kept:** the *linking* idea (associating related episodic memories) is logged as a
  `defer` candidate for a later week, to revisit only after the citation-preserving consolidation
  path is measured. Its evolution mechanism is explicitly rejected.

### I6 — LLMLingua compression · **REJECT (v1)**
- **Why reject:** the injection budget is already small (≤2k tokens) and we store compact typed
  facts, not raw chunks, so there is little redundancy left to compress; adding a compressor model
  costs latency and complexity for marginal budget gain.
- **Revisit condition:** if a later design admits longer free-text memories or the budget shrinks
  materially, re-open.

---

## Highest-value idea → proposed amendment (handbook §4.2 step 8)

**I1 (bi-temporal validity + supersession-by-invalidation)** is the highest-value adopt: it fixes
the failure (F4) on which the justification for the most important component (C5) rests, at low
runtime cost, and it produces a *cleaner architecture* by moving conflict resolution off the
ranker. The design amendment and its ADR are `design_opportunities.pdf` and
`../../design/decision_records/ADR-001-bitemporal-validity.md`. Its bounded validation runs inside
Deliverable 3.
