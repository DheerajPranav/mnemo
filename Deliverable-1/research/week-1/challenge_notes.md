# Week 1 — Challenge Notes

**Deliverable 2, Week 1 design-opportunity review** · Dheeraj Pranav · 22 July 2026

Handbook §4.3 requires the strongest technical challenges to each proposal, the answers that
*changed* after discussion, and the final disposition. There was no live audience this week, so
this is an honest self-adversarial pass: each proposal is attacked using the §4.3 probe set, and
where the attack moved my position I say so explicitly rather than defending the original.
The lead challenge is a real, recent, adversarial source (arXiv:2604.11628) chosen deliberately.

Probe set (§4.3): (a) which observed problem does it solve · (b) does the evidence transfer to our
conditions · (c) which assumptions must stay true · (d) would a simpler change do the same · (e)
what complexity/latency/cost/privacy/reliability risk · (f) how tested before integration · (g)
what evidence would reverse it.

---

## Challenge 0 (lead) — "Is any of this necessary?" — *Back to Basics* (arXiv:2604.11628, 2026)

**The challenge.** This 2026 paper argues the bottleneck in conversational memory is a *Signal
Sparsity Effect*, not memory architecture, and that a minimalist retrieval+generation pipeline
(Turn-Isolation Retrieval + Query-Driven Pruning) beats stronger memory baselines while using
fewer tokens and less latency. If true, the entire admission/representation/lifecycle stack this
project proposes is over-engineered, and I should build the minimalist thing.

**My answer, and what changed.**
- **What did not change:** the paper's benchmarks are memory *recall* tasks. It does **not**
  address the failures that drive *this* design — F10 cross-tenant leakage, F11 incidental PII, F9
  tested deletion. Those are not accuracy problems that a better retriever fixes; they are
  invariants with legal/existential consequences (`failure_analysis §6`, the five unrecoverable
  rows). A minimalist retriever with no admission gate cannot satisfy them at any accuracy. So the
  paper does not refute the design's core.
- **What did change (genuinely):** it moved my position on the **baseline** and on **scope
  honesty**. (1) It is strong evidence that the Day-3 naive baseline must be a *good* minimalist
  retriever, not a straw man — "Turn-Isolation Retrieval" is a fairer, stronger baseline than
  naive global top-k, so I will note it as a baseline-strengthening candidate. (2) It sharpens
  falsifier 1: if a minimalist retriever already handles knowledge-updates well on my fixed set,
  then I1 (temporal model) is not earning its cost and must be cut. I had been treating I1 as
  near-certain; I now hold it as *adopt-pending-D3-measurement*.
- **Disposition:** the paper is **tracked as a standing challenge**, its retrieval idea is a
  `defer` baseline-strengthening candidate, and it is written into the D3 protocol as the reason
  the baseline gets a fair, strong retriever.

---

## Challenge 1 — I1 bi-temporal validity

- **(a) Problem:** F4 superseded fact served as current.
- **(b) Evidence transfer:** Zep's gains are on LongMemEval/DMR (assistant chat + business data) —
  *closer* to GTM than Generative Agents' simulation, but still not multi-tenant and not
  regulated. So the mechanism transfers; the *magnitude* does not. `inference`
- **(d) Simpler alternative — strongest form of the challenge:** "Just add a recency weight to the
  ranker and skip the whole validity model." **This changed my framing.** A recency weight cannot
  express *supersession* (fact X was replaced by fact Y specifically), only *newer-is-better*,
  which is wrong when an old fact is still valid and a newer utterance is noise. But the challenge
  is right that I must *prove* the ranker-only version fails before paying for the schema — so the
  D3 experiment now compares three arms: naive similarity, similarity+recency, and validity-filter.
  If similarity+recency closes the gap, I1 loses.
- **(e) Risk:** the invalidation write is irreversible-ish (though history is preserved) and rests
  on contradiction detection at admission, which can be wrong — an incorrectly invalidated fact
  disappears from retrieval. This is `first_principles` open question 2, now with teeth.
- **(g) Reversal:** D3 shows similarity+recency ≈ validity-filter on the fixed set.

## Challenge 2 — I2 LongMemEval as eval scaffold

- **(b) Transfer / (c) assumptions:** LongMemEval has no cross-tenant or PII abilities, so adopting
  it wholesale would give false confidence that the hardest GTM failures are covered. **Position
  changed from "adopt" to "adopt taxonomy + subset, then extend"** precisely because of this probe.
- **(d) Simpler:** "hand-write 20 cases." Rejected — that is how you get a set that only tests what
  you already expect; borrowing an external taxonomy imports failure types (abstention) I might
  under-weight.
- **(g) Reversal:** if the borrowed cases saturate (all-pass or all-fail) on the naive baseline,
  they measure nothing and get replaced with harder GTM-authored cases.

## Challenge 3 — I3 Presidio PII gate

- **(d) Simpler:** "regex only." Partially accepted — regex handles structured PII (cards, emails)
  cheaply; Presidio's NER adds names/locations at higher cost. Disposition: start with the
  deterministic recognizers, treat NER recognizers as optional/config, measure recall.
- **(e) Reliability risk:** false negatives leak PII into the store. **This reinforced, not changed,
  the design:** deletion (C7) stays as the backstop; the gate is defence-in-depth, not a sole
  guarantee. `inference`
- **(f) Tested:** labelled PII pos/neg set in D6; precision/recall reported.

## Challenge 4 — I4 Mem0 operation selector (prototype)

- **(b) Evidence transfer — the decisive probe:** Mem0's 90%+ savings are vs *full-context*, not
  vs our naive RAG baseline. Quoting that number as if it argued for adoption here would be exactly
  the "use generated trend lists without inspecting the source" failure the handbook §12 warns
  about. Kept as **prototype**, with the cost measured against *our* baseline, not theirs.
- **(g) Reversal:** write-path LLM cost breaches the ≤15% envelope without a matching
  update-accuracy gain → drop the LLM selector for a cheaper rule + embedding-similarity heuristic.

## Challenge 5 — I5 A-MEM evolution (deferred) & I6 LLMLingua (rejected)

- **I5:** the challenge "you're rejecting a SOTA result" is answered by naming the invariant it
  breaks (C7 cite-don't-replace ⇒ F5/F6). A SOTA number in a no-regulation setting does not buy
  back an unrecoverable failure mode in a regulated one. Disposition unchanged: **defer** the link
  idea, **reject** the evolution/mutation step.
- **I6:** the challenge "compression is free quality" is answered by scale — at ≤2k tokens of
  compact typed facts there is little to compress. Disposition unchanged: **reject v1**, revisit if
  budget/representation changes.

---

## Summary of position changes (what this review actually moved)

| Proposal | Before review | After review |
| :-- | :-- | :-- |
| I1 temporal model | adopt (near-certain) | **adopt, pending D3 3-arm comparison** (naive / +recency / validity) |
| I2 eval scaffold | adopt wholesale | **adopt taxonomy + subset, extend for GTM** |
| I3 PII gate | adopt (Presidio full) | **adopt deterministic-first, NER optional; deletion as backstop** |
| Baseline design | naive global top-k | **strengthen with Turn-Isolation Retrieval** (from Challenge 0) |
| Whole-system necessity | assumed | **explicitly defended against a real 2026 counter-argument** |

Two of these (the 3-arm D3 comparison, and strengthening the baseline retriever) are concrete
changes to the Deliverable 3 protocol, made *because* of the challenge — which is the point of the
exercise.
