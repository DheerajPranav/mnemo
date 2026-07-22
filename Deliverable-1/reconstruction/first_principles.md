# First-Principles Derivation of Required System Capabilities

**Project:** Conversational Memory Intelligence System
**Grounding domain:** GTM AI (B2B SaaS revenue teams)
**Author:** Dheeraj Pranav
**Date:** 19 July 2026
**Companion documents:** `failure_analysis.md`, `problem_reconstruction.pdf`, `historical_timeline.pdf`

---

## Method, and why it is worth the trouble

`failure_analysis.md` works backwards: it takes four known designs, breaks them, and reads
requirements off the wreckage. That method is honest but it inherits the shape of whatever it
broke. If all four prior approaches share a blind spot, so will the requirements derived from
them.

This document works forwards instead. It starts from properties of the setting that I believe
hold regardless of implementation, derives capabilities from those, and only at the end
compares the result against the failure-driven list. Agreement is evidence. Disagreement is
the interesting part, and Section 5 records it rather than smoothing it over.

Nothing here names a technology. No vector database, no embedding model, no framework. If a
capability below cannot be stated without naming a tool, it is a design decision that has
leaked into the requirements, and it belongs in Deliverable 4.

---

## 1. Premises

Eight properties of the setting. Each is either analytic (true by the nature of the system) or
empirical (true of my deployment, and falsifiable).

### P1. The model is a pure function of its context. *(analytic)*

A model call maps input tokens to output tokens. It has no side effects on itself and no
recollection of prior calls. Any continuity between turn `t` and turn `t+1` exists because
something outside the model wrote it down and put it back in.

> Consequence: memory is not a model capability that we are failing to invoke. It is
> infrastructure that does not exist unless built.

### P2. Context is finite and monotonically costly. *(analytic + empirical)*

Every model has a maximum input length, and price and latency both increase with input length.
`[VERIFIED]` Liu et al. (arXiv:2307.03172) additionally show that *usable* context is smaller
than nominal context, because retrieval accuracy from the middle of a long input degrades.

> Consequence: injection is a constrained selection problem, not a copying problem. There is a
> budget, and something must decide what spends it. Growing the window changes the budget's
> size and nothing else about the problem's structure.

### P3. Conversation is a low-precision, high-redundancy source. *(empirical)*

What arrives is utterances: hedged, contradictory, repetitive, context-dependent, mixed with
scheduling chatter. Value per token is low and very unevenly distributed.

> Consequence: there must be a decision about what enters the system. "Store everything" is not
> the absence of a policy, it is a policy, and it is the one that maximises noise.

### P4. Facts have validity intervals, and the world revises them. *(empirical)*

"Acme uses Salesforce" was true in February 2025 and false in April 2026. Buyers change tools,
people change jobs, budgets change, and requirements are withdrawn. In a revenue system the
rate of change is high and the cost of acting on a stale fact is direct.

> Consequence: a memory is not a proposition. It is a proposition plus a time interval plus a
> relation to other memories that may supersede it. Any representation that stores only the
> proposition has discarded the information needed to use it correctly.

### P5. Tenants are mutually distrusting and share infrastructure. *(empirical)*

Two customer organisations may both sell to a company called Acme. Their notes are lexically
near-identical and commercially confidential from each other.

> Consequence: isolation is an invariant, not a feature. An invariant is something no code path
> can violate, which is a stronger requirement than something every code path remembers to check.

### P6. Some observed information is ineligible for retention, and eligibility is revocable. *(empirical)*

Personal data appears incidentally in sales conversations. Retention rights can be withdrawn
by the data subject or ended by contract.

> Consequence: there must be an admission gate before storage, and a deletion path that
> reaches every copy, with a stated and tested consistency window. A guarantee that has not
> been tested is not a guarantee.

### P7. The system's decisions are not observable in its output. *(analytic)*

A user sees an answer. They do not see which memories were candidates, which were retrieved,
which were dropped for budget, or which were suppressed by policy. When the answer is wrong,
the output alone does not identify which stage failed.

> Consequence: every stage decision must be emitted as a structured event. Otherwise debugging
> is guesswork and the failure taxonomy in Deliverable 3 cannot be populated from real traffic.

### P8. Retrieval quality is distributional, not per-query. *(analytic)*

"The system retrieved the right memory" for one query is an anecdote. Quality is a property of
the distribution of queries.

> Consequence: a fixed evaluation set, offline and reproducible, plus comparison against a
> baseline. A system that cannot be measured against its predecessor cannot be claimed to
> improve on it.

---

## 2. Derivation

Each capability is stated as what the system must do, followed by the premises that force it
and the failures from `failure_analysis.md` it addresses. The derivation is intended to be
checkable: if a premise is removed, the capabilities that cite it should become optional.

### C1. Durable write of conversational information

Extract candidate memories from conversation and persist them outside the model, across
sessions.

- **Forced by:** P1 (nothing persists otherwise).
- **Addresses:** F1.
- **Sharpest form:** an explicit user correction must be durable, because a correction is the
  highest-confidence signal the system will ever receive about the world. If nothing else is
  written, corrections are written.

### C2. Admission policy, not blanket capture

Decide per candidate whether it is stored, with a typed outcome: store, update an existing
memory, or discard. The policy is a named, inspectable artifact.

- **Forced by:** P3 (redundancy and low value density), P6 (ineligible information exists).
- **Addresses:** F8, F11.
- **Note:** P6 makes this a hard gate rather than an optimisation. Post-hoc redaction cannot
  work, because by the time output is filtered the data is already in the index and in backups.

### C3. Typed representation with provenance, confidence, and validity

Store resolved claims, not raw spans. Each memory carries at minimum: type, subject, content,
source reference, confidence, observation time, validity interval, and tenant.

- **Forced by:** P3 (utterances invert out of context), P4 (validity is part of the fact),
  P6 (deletion needs provenance to find every copy), P7 (traces need identity).
- **Addresses:** F5, F7, F4.
- **Note:** provenance is what makes compression safe. A consolidated memory that cites its
  sources can be re-derived; one that replaces them cannot.

### C4. Source of truth separate from retrieval index

Maintain an authoritative store, with the index treated as a derived, rebuildable projection.

- **Forced by:** P6 (deletion must be authoritative somewhere), P8 (re-indexing is required to
  evaluate index changes without losing data).
- **Addresses:** F9.
- **Note:** this is the capability that makes the deletion consistency window a measurable
  quantity rather than a hope. It also means an embedding-model change is a re-projection, not
  a migration.

### C5. Multi-signal ranking with explicit conflict resolution

Rank candidates on relevance, recency, importance, and confidence, and resolve contradictions
using validity intervals and supersession rather than letting both survive into context.

- **Forced by:** P4 (similarity cannot express validity), P3 (relevance alone over-selects
  duplicates).
- **Addresses:** F4, F8.
- **Prior art:** `[VERIFIED]` Park et al. (arXiv:2304.03442) combine relevance, recency, and
  importance. `[INFERENCE]` Their setting has no contradicting-preference problem and no
  confidence signal, so conflict resolution and confidence are additions I am proposing, not
  things they demonstrate.

### C6. Budgeted context construction

Select and order the final memory set under an explicit token budget, with defined behaviour
when the budget binds and when nothing relevant is found.

- **Forced by:** P2 (finite, costly, position-sensitive context).
- **Addresses:** F2, F3.
- **Note:** P2's position-sensitivity means ordering is part of the capability, not a detail.
  Placing the highest-value memory in the middle of a long injection wastes it.
- **Prior art:** `[VERIFIED]` Packer et al., MemGPT (arXiv:2310.08560), treat context as a
  managed resource with a hierarchy and paging. `[INFERENCE]` The useful transfer is the framing
  of context as a budget with an allocator, not the specific paging mechanism.

### C7. Lifecycle: update, consolidate, decay, expire, delete

Support correction of existing memories, consolidation of related ones with citation back to
sources, decay of unused low-importance memories, expiry at validity end, and hard deletion on
request.

- **Forced by:** P4 (the world revises facts), P6 (revocable eligibility), P3 (redundancy
  accumulates without consolidation).
- **Addresses:** F1, F6, F9.
- **Note:** consolidation must cite rather than replace, or it reintroduces F5 and F6. This is
  the direct lesson from Approach C in the failure analysis.

### C8. Isolation as an invariant

Enforce tenant separation below the retrieval API, so that no query path can express a
cross-tenant read. Log every access.

- **Forced by:** P5.
- **Addresses:** F10.
- **Note:** stated as "no path exists" rather than "every path filters." The difference is the
  entire security posture. `[INFERENCE]` A post-retrieval filter also silently degrades recall,
  because foreign memories consume top-k slots before being discarded, so the weak form fails
  on quality grounds as well as safety grounds.

### C9. Decision observability

Emit a structured trace per request: candidates considered, scores by signal, selections,
budget-driven drops, policy suppressions, and the final injected set.

- **Forced by:** P7.
- **Addresses:** all of them, indirectly. This is the capability that makes the others
  debuggable in production rather than only in test.

### C10. Reproducible offline evaluation against a baseline

Maintain a fixed, versioned evaluation set with adversarial cases (distractors, superseded
preferences, cross-tenant near-duplicates, PII, cold start), and report component and
end-to-end metrics against the naive baseline.

- **Forced by:** P8.
- **Addresses:** the credibility of every claim made about the other nine.
- **Note:** the handbook makes baseline comparison a non-negotiable gate. P8 says the same
  thing from the other direction: without a fixed distribution, improvement is not a
  well-formed claim.

---

## 3. Cross-check against the failure-driven requirements

Every failure F1 to F11 maps to at least one capability, and every capability C1 to C10 is
forced by at least one premise. Neither list contains an orphan.

| Failure | Capabilities |
| :-- | :-- |
| F1 correction does not persist | C1, C7 |
| F2 quadratic prompt cost | C6 |
| F3 mid-context facts unused | C6 |
| F4 superseded fact served as current | C3, C5 |
| F5 rare detail lost to summarisation | C3, C4, C7 |
| F6 summary drift, false confidence | C3, C7 |
| F7 chunk inverts out of context | C3 |
| F8 index saturated with duplicates | C2, C5, C7 |
| F9 deleted memory still retrievable | C4, C7 |
| F10 cross-tenant read | C8 |
| F11 sensitive data retained | C2, C8 |

| Capability | Premises |
| :-- | :-- |
| C1 durable write | P1 |
| C2 admission policy | P3, P6 |
| C3 typed representation | P3, P4, P6, P7 |
| C4 source of truth vs index | P6, P8 |
| C5 multi-signal ranking | P3, P4 |
| C6 budgeted construction | P2 |
| C7 lifecycle | P3, P4, P6 |
| C8 isolation invariant | P5 |
| C9 observability | P7 |
| C10 offline evaluation | P8 |

---

## 4. Constraint envelope

Requirements are meaningless without numbers to violate. `[ASSUMPTION]` Every figure below is a
target I am setting now so that Deliverable 3 can measure against something and Deliverable 4
can design against something. None is measured. All are revisable with a recorded reason.

| Dimension | Target | Basis |
| :-- | :-- | :-- |
| Memory injection budget | ≤ 2,000 tokens of a 16,000-token working context | ~12%, leaves room for instructions, tools, and the turn itself |
| Memory subsystem latency | p95 ≤ 300 ms (retrieve, rank, construct) | Fits inside a ~3 s perceived-instant agent turn |
| Memory subsystem cost | ≤ 15% of per-turn token spend | Above this the feature is hard to justify per seat |
| Scale | 50 tenants x 200 users x 10,000 memories = 10^8 memories | Mid-market B2B SaaS deployment |
| Deletion consistency | ≤ 60 s typical, ≤ 24 h guaranteed and tested | Guarantee must be one I can actually meet |
| Cross-tenant leakage | Zero, tested adversarially | P5 admits no tolerance |
| Retrieval quality | Beat naive baseline on the fixed set | P8; the specific metric is set in Deliverable 3 |

The relationship between the first three is the real design tension. Budget, latency, and cost
all push toward retrieving less; correctness pushes toward retrieving more. Ranking quality is
what buys correctness without spending budget, which is why C5 is the component most worth
investing effort in.

---

## 5. Where the two derivations disagree

The point of doing this forwards as well as backwards.

**C9 and C10 are underdetermined by the failure analysis.** Neither observability nor offline
evaluation appears as a fix for any specific failure F1 to F11. They arrive only from P7 and
P8. `[INFERENCE]` This is exactly the blind spot I expected from a purely failure-driven
method: breaking four prior designs surfaces the failures those designs can exhibit, not the
failures I would be unable to *detect*. A capability whose absence causes silent
undetectability cannot be discovered by observing failures. That is a genuine finding about
method, and it is the strongest argument for having written this document.

**F5 and F6 are over-determined.** Summarisation loss and drift are addressed by C3, C4, and
C7 together, and no single premise forces the full fix. `[INFERENCE]` This suggests
consolidation is the highest-risk component in the design, because it is where three
capabilities have to cooperate correctly. It should get the earliest and most adversarial
testing, ahead of components that look harder but are more self-contained.

**P4 does more work than expected.** Validity and supersession force parts of C3, C5, and C7.
`[INFERENCE]` If I had to cut scope, temporal validity is the last thing to cut, ahead of
importance scoring or reflection. This contradicts my initial instinct, which was that
reflection was the interesting part. It is the part that is interesting to read about, not the
part that carries the system.

---

## 6. What would falsify this derivation

Stating this now, before the baseline exists, so it cannot be adjusted afterwards.

1. If the naive baseline in Deliverable 3 handles superseded preferences correctly at a rate
   comparable to a multi-signal ranker on the fixed set, then P4 does not force C5 in
   practice, and the ranking complexity is not earning its cost.
2. If extraction into typed facts (C3) produces more total errors than chunk retrieval, and the
   errors are more confidently stated, C3 is net harmful and the design should keep chunks with
   validity metadata attached instead.
3. If admission filtering (C2) discards memories that later prove necessary at a measurable
   rate, then P3 was overstated for this domain, and the correct default shifts back toward
   storing more with better ranking rather than storing less.
4. If the deletion consistency window cannot be held under load, C4's separation is not
   delivering its main justification and the architecture needs a single-store reconsideration.
5. If observability (C9) produces traces that never actually localise a failure during
   Deliverable 6, then P7's consequence was wrong and the tracing is ceremony.

Each of these is a real experiment, not a rhetorical hedge. Numbers 1 and 2 are cheap and run
inside Deliverable 3. Numbers 3, 4, and 5 need the full implementation and land in Deliverable 6.

---

## 7. Deliberate non-goals

Stated so that Deliverable 4 does not quietly expand.

- **Not a general knowledge base.** Only information observed in conversation, not the
  vendor's product documentation. Documentation retrieval is a separate corpus with different
  freshness and ownership properties.
- **Not learned retrieval.** Ranking signals are hand-specified and inspectable in the first
  version. A learned ranker requires labelled data that does not exist yet, and it would make
  C9 much harder.
- **Not real-time cross-user memory sharing.** Team-level shared memory raises consent and
  access-control questions that P5 and P6 do not yet answer. Deferred, with the reason recorded.
- **Not model-agnostic in the first version.** One provider, one embedding model, behind a
  swappable interface. P8 requires reproducibility, and pinning is the cheapest way to get it.

---

## 8. Sources

1. Liu, N. F., Lin, K., Hewitt, J., et al. *Lost in the Middle: How Language Models Use Long
   Contexts.* 2023. https://arxiv.org/abs/2307.03172
2. Park, J. S., O'Brien, J. C., Cai, C. J., et al. *Generative Agents: Interactive Simulacra of
   Human Behavior.* 2023. https://arxiv.org/abs/2304.03442
3. Packer, C., Wooders, S., Lin, K., et al. *MemGPT: Towards LLMs as Operating Systems.* 2023.
   https://arxiv.org/abs/2310.08560
4. Lewis, P., Perez, E., Piktus, A., et al. *Retrieval-Augmented Generation for
   Knowledge-Intensive NLP Tasks.* 2020. https://arxiv.org/abs/2005.11401

**AI assistance disclosure.** Claude was used to draft prose and stress-test the derivation.
The premises, the capability derivation, the falsification conditions in Section 6, and the
method finding in Section 5 are mine and are what I will defend in review.
