# Failure Analysis: Why Simpler Conversational Memory Designs Break

**Project:** Conversational Memory Intelligence System
**Grounding domain:** GTM AI (B2B SaaS revenue teams)
**Author:** Dheeraj Pranav
**Date:** 19 July 2026
**Status:** Deliverable 1 of 8, Learning Through Reconstruction handbook v1.0

---

## Evidence key

Every claim below carries one of four tags. The handbook requires that what a source
demonstrates, what its authors infer, and what I propose stay separable.

| Tag | Meaning |
| :-- | :-- |
| `[VERIFIED]` | Stated in a cited paper or in my own production experience, with the source named. |
| `[INFERENCE]` | My reading of what the cited evidence implies for this system. Not claimed by the source. |
| `[ASSUMPTION]` | A working assumption about my deployment setting. Unmeasured. Must be tested in Deliverable 3. |
| `[TO MEASURE]` | A claim I deliberately refuse to assert until the naive baseline produces a number. |

Nothing in this document reports a benchmark result. The naive baseline has not been built
yet. Deliverable 3 replaces every `[TO MEASURE]` with a measured value or retracts the claim.

---

## 0. The setting, in one paragraph

A GTM assistant sits inside a B2B SaaS vendor's revenue stack. Its users are account
executives, SDRs, and RevOps analysts. It prepares call briefs, answers questions about an
account's history, and drafts follow-ups. It is multi-tenant: the vendor sells the assistant
to many customer organisations, and each customer's account data, call transcripts, and buyer
notes sit on shared infrastructure. A single user touches dozens of accounts per week and
returns to any given account after gaps of days or months.

This setting is chosen deliberately. It is the domain I have worked in for six years, it
supplies naturally adversarial conditions (near-duplicate accounts, preferences that expire,
regulated personal data, hard isolation requirements), and it makes the failure cases below
concrete rather than hypothetical.

---

## 1. Approach A: Stateless prompting

**What it is.** Each turn is an independent model call. The prompt contains the system
instruction, the current user message, and nothing else. Any context the model needs, the
user restates.

**Assumptions it makes.**

- A1. Everything required to answer fits in what the user is willing to type each time.
- A2. The user is a reliable and low-cost source of their own history.
- A3. Corrections are a property of the conversation, not of the world.

**Why A3 is the load-bearing one.** A stateless design treats "you got that wrong, Ravi left
Acme in March" as a message. It is not a message. It is a durable update to a fact about the
world that must outlive the session in which it was uttered.

### Failure case A-1: the correction that never sticks

```
Session 1 (12 May)
  AE:     Prep me for the Acme renewal call.
  Agent:  ... primary contact Ravi Menon, VP Engineering ...
  AE:     Ravi left in March. Priya Raghavan owns this now.
  Agent:  Understood, updating.        <- updates nothing

Session 2 (19 May, new session)
  AE:     Prep me for the Acme renewal call.
  Agent:  ... primary contact Ravi Menon, VP Engineering ...
```

The same correction is issued in sessions 3, 4, and 5. `[ASSUMPTION]` In a GTM setting I
expect the AE to abandon the tool after roughly the third repetition, because the cost of
correcting it exceeds the cost of doing the prep manually. This is an adoption failure, not
an accuracy failure, and it is the one that actually kills internal AI tools.

`[VERIFIED]` This mirrors what I observed on the Novartis Decision Engine: field
representatives ignored recommendations they could not understand or could not influence.
Adoption is gated on the system visibly incorporating what the user tells it.

**Violated assumption:** A3. **Impact:** correctness (stale fact served as current) and
abandonment.

### Failure case A-2: the invisible cost of restating

`[INFERENCE]` A stateless design does not remove the token cost of context, it transfers it
to the user. The AE who pastes three paragraphs of account background into every session is
running a manual, unreliable, unversioned memory system. `[TO MEASURE]` The baseline should
record how many prompt tokens are user-supplied restatement versus new intent.

**Minimum capability this failure implies:** durable, cross-session write of facts asserted or
corrected during conversation.

---

## 2. Approach B: Full conversation replay

**What it is.** Persist the entire transcript per user per account and prepend all of it to
every call. No selection, no compression.

**Assumptions it makes.**

- B1. The context window is large enough for the full history.
- B2. Attention is a sufficient relevance mechanism, so no explicit selection is needed.
- B3. Cost and latency scale acceptably with history length.

### Failure case B-1: quadratic cost against a linear conversation

Within a single session of `n` turns, replaying everything means turn `k` carries roughly
`k` turns of history, so total prompt tokens across the session grow as O(n²) while the
conversation itself grows as O(n). `[VERIFIED]` This is arithmetic, not an empirical claim.
For an enterprise account with three years of call transcripts and email threads, B1 fails
outright before B3 even becomes interesting.

### Failure case B-2: recall degrades in the middle of a long context

`[VERIFIED]` Liu et al., *Lost in the Middle: How Language Models Use Long Contexts*
(arXiv:2307.03172), show that model accuracy on retrieving a fact from a long context is
strongly position-dependent, and is worst when the relevant fact sits in the middle of the
input rather than at either end.

`[INFERENCE]` Applied here: a buyer objection raised in month two of an eighteen-month deal
cycle lands in the exact position where the model is least likely to use it. B2 therefore
fails. A longer window does not make selection unnecessary, it makes selection quieter about
failing. This is the single most important argument against "just wait for bigger context
windows."

### Failure case B-3: stale and current facts carry equal weight

Replay is chronological, not epistemic. The transcript contains both:

```
2025-02-11  "We're a Salesforce shop, everything routes through SFDC."
2026-04-30  "We finished the HubSpot migration last quarter."
```

Nothing in the representation marks the first as superseded. `[TO MEASURE]` Whether the model
resolves this correctly from recency cues alone is exactly the kind of claim I will not assert
without the baseline number. My expectation is that it resolves it inconsistently, and that
inconsistency is worse than uniform failure because it cannot be trained around.

**Violated assumptions:** B1, B2, B3. **Impact:** cost, latency, correctness.

**Minimum capabilities implied:** selection under an explicit token budget; explicit temporal
validity on stored facts.

---

## 3. Approach C: Rolling summarisation

**What it is.** Keep a running summary. Every `k` turns, feed the summary plus recent turns
to the model and ask for an updated summary. Inject only the summary.

**Assumptions it makes.**

- C1. Summarisation is a lossy compression whose losses are unimportant.
- C2. What matters is roughly what is recent or frequently repeated.
- C3. The summariser is accurate enough that errors do not accumulate.

### Failure case C-1: irreversible loss of the rare and important

C1 and C2 conflict for exactly the facts a GTM system exists to hold. A buyer's single stated
disqualifier ("legal will not approve anything that stores data outside the EU") is mentioned
once, never repeated, and is decisive. A summariser optimising for the gist of a conversation
drops single-mention details preferentially, because that is what compression means.

`[INFERENCE]` Compression that is not selective by importance will preferentially discard
low-frequency, high-consequence facts. The rarity that makes a fact easy to drop is
uncorrelated with the stakes attached to it. This is the core structural objection to
summarisation as a memory primitive.

Once dropped at summarisation round 3, the fact is unrecoverable at round 12. There is no
path back to the source.

### Failure case C-2: error compounding through self-ingestion

Each summarisation round reads the previous summary as if it were ground truth. An error
introduced at round `k` is not merely retained, it is treated as an established fact by every
subsequent round and is progressively stripped of the hedging that might have flagged it.

```
Round 3   "Priya mentioned budget might land around 40k, not confirmed."
Round 6   "Budget approximately 40k."
Round 11  "Budget: 40k (confirmed)."
```

`[INFERENCE]` The system manufactures confidence it never had. C3 fails, and it fails silently,
because the output at round 11 is more fluent and more assertive than the honest output at
round 3. `[TO MEASURE]` Drift rate and direction on a fixed transcript set.

**Violated assumptions:** C1, C2, C3. **Impact:** correctness, and a confidence signal that is
anti-correlated with truth.

**Minimum capabilities implied:** source-of-truth storage that survives compression;
provenance and confidence attached to every memory; consolidation that cites its sources
rather than replacing them.

---

## 4. Approach D: Naive retrieval-only (single-signal RAG over transcript chunks)

This is the strongest of the simpler approaches and therefore the one the baseline in
Deliverable 3 will actually implement. `[VERIFIED]` Lewis et al., *Retrieval-Augmented
Generation for Knowledge-Intensive NLP Tasks* (arXiv:2005.11401), establish the pattern:
embed a corpus, embed the query, retrieve top-k by vector similarity, condition generation on
the result.

**What it is here.** Chunk every transcript, embed, store all chunks, retrieve top-k by cosine
similarity to the current user message, inject.

**Assumptions it makes.**

- D1. Semantic similarity to the current query is an adequate proxy for what belongs in context.
- D2. The corpus is static, internally consistent, and worth storing in full.
- D3. Chunks are self-contained units of meaning.
- D4. Nothing in the corpus is ineligible for retention.

Each of these is false in this setting, and each falsifies differently.

### Failure case D-1: similarity cannot express recency or supersession (D1, D2)

Query: *"What CRM does Acme use?"*

| Retrieved chunk | Date | Cosine | Truth |
| :-- | :-- | :-- | :-- |
| "We're a Salesforce shop, everything routes through SFDC." | 2025-02-11 | 0.91 | superseded |
| "We finished the HubSpot migration last quarter." | 2026-04-30 | 0.84 | current |

The superseded fact scores higher, because it is phrased more directly on-topic. Similarity is
a statement about wording, not about validity. `[INFERENCE]` No amount of embedding quality
fixes this, because the ordering is correct with respect to the objective the embedder was
trained on. The fix has to live outside the similarity signal: an explicit temporal validity
field and a supersession relation between memories.

`[VERIFIED]` Park et al., *Generative Agents* (arXiv:2304.03442), demonstrate a retrieval score
combining relevance, recency, and importance rather than relevance alone. That is direct
evidence that single-signal ranking is insufficient even in a far less adversarial setting than
a revenue system.

### Failure case D-2: chunks are not facts (D3)

A transcript chunk is an utterance. Utterances invert under context.

```
Chunk retrieved:  "I don't think we need SSO for the pilot."
Actual exchange:  AE:    Should we scope SSO into the pilot?
                  Buyer: I don't think we need SSO for the pilot.
                  AE:    Security will probably push back.
                  Buyer: Fair. Put it in. Non-negotiable for prod.
```

Injected alone, the chunk asserts the opposite of the account's actual position. `[INFERENCE]`
The unit of storage must be an extracted, typed, resolved claim ("Acme requires SSO for
production, not for pilot"), not a span of raw text. This is the argument for an extraction and
admission stage, and it is independent of every ranking concern above.

### Failure case D-3: no admission control collapses precision (D2)

Storing everything means storing scheduling chatter, pleasantries, and repeated
recitations of the same fact from six calls. `[INFERENCE]` The index becomes mostly noise, and
top-k fills with near-duplicate low-value chunks that crowd out the one chunk that mattered.
Recall at k is bounded by how many of the k slots are wasted. `[TO MEASURE]` Proportion of
retrieved slots occupied by non-informative or duplicate content in the baseline.

### Failure case D-4: deletion does not propagate (D4)

The user exercises a right to erasure, or an account is offboarded. The row is deleted from the
source store. The embedding remains in the vector index, and the chunk keeps surfacing.
`[INFERENCE]` Deletion in a dual-store architecture is a distributed operation with a
consistency window, and if that window is not specified and tested, the system has no
erasure guarantee at all, only an erasure gesture. The handbook makes this a non-negotiable
gate, correctly.

### Failure case D-5: cross-tenant leakage under near-duplicate queries (D4)

Two customer organisations of the vendor each sell to a company called Acme. Their notes are
lexically near-identical. If the tenant filter is applied as a post-retrieval re-rank rather
than as a pre-filter on the index, top-k can be entirely filled by the wrong tenant's memories
and return empty after filtering, or worse, return them.

`[INFERENCE]` Isolation implemented as filtering is a correctness bug waiting to happen.
Isolation has to be an index-partitioning invariant, enforced below the retrieval API, so that
no query path exists that can express a cross-tenant read.

### Failure case D-6: sensitive data admitted by default (D4)

A buyer mentions a colleague's medical leave on a discovery call. The transcript is chunked,
embedded, and stored indefinitely. Nobody decided this. It happened because the default was
"store everything."

`[INFERENCE]` PII handling cannot be a downstream redaction filter on the output. By the time
it is on the output path, the data is already in the index, already in backups, and already
outside the deletion window. Admission is the only correct place to enforce it.

**Violated assumptions:** D1, D2, D3, D4. **Impact:** correctness, precision, legal exposure,
and the two failure modes (cross-tenant read, unfulfilled deletion) that are unrecoverable
rather than merely bad.

---

## 5. Approach E: Long-context models as a substitute for memory

Included because it is the most common objection to building any of this.

**What it is.** Use a model with a very large context window. Put everything in. Skip the
memory system.

**Assumptions it makes.**

- E1. Window size is the binding constraint.
- E2. Cost and latency at full window are acceptable.
- E3. A window is a place to keep things.

### Why it fails

`[VERIFIED]` Liu et al. (arXiv:2307.03172) already falsify the naive form of E1: usable recall
is position-dependent and degrades in the middle, so effective capacity is smaller than nominal
capacity.

`[INFERENCE]` E3 is the deeper error. A context window is per-request working memory. It is
not storage. It has no persistence across requests, no write path, no deletion semantics, no
tenant boundary, no audit trail, and no consolidation. Every capability this project exists to
provide is a property the window does not have at any size. Growing the window changes the
budget of the selection problem. It does not remove the selection problem, and it does not
touch the lifecycle, isolation, or observability problems at all.

`[ASSUMPTION]` Cost per turn scales with input tokens, so a full-window strategy converts a
selection problem into a recurring bill. In a GTM tool priced per seat, that bill is the
product's margin.

**Impact:** cost, and a false sense that the problem is solved.

---

## 6. Failure taxonomy

Consolidated view. Each row is `observed failure -> violated assumption -> impact`, in the
form the handbook's productive-failure template requires. Deliverable 3 measures the
frequency of each against the baseline.

| # | Observed failure | Violated assumption | Primary impact | Recoverable? |
| :-- | :-- | :-- | :-- | :-- |
| F1 | Correction does not survive the session | A3 (corrections are conversational) | Adoption | Yes |
| F2 | Prompt cost grows quadratically in session length | B3 (cost scales acceptably) | Cost | Yes |
| F3 | Mid-context facts are not used | B2 (attention suffices as selection) | Correctness | Yes |
| F4 | Superseded fact served as current | B2, D1 (similarity encodes validity) | Correctness | Yes |
| F5 | Rare high-stakes detail lost in summarisation | C1, C2 (losses are unimportant) | Correctness | **No** |
| F6 | Summary drift manufactures false confidence | C3 (summariser errors do not accumulate) | Correctness, calibration | **No** |
| F7 | Retrieved chunk inverts meaning out of context | D3 (chunks are self-contained) | Correctness | Yes |
| F8 | Index saturated with low-value duplicates | D2 (store everything) | Precision, cost | Yes |
| F9 | Deleted memory still retrievable | D4 (deletion is a source-store operation) | Legal, trust | **No** |
| F10 | Cross-tenant memory returned | D4 (filtering implies isolation) | Legal, existential | **No** |
| F11 | Sensitive data retained without a decision | D4 (nothing is ineligible) | Legal | **No** |

The five unrecoverable rows are the ones that shape the architecture. A system can tolerate
retrieving a mediocre memory. It cannot tolerate retrieving another tenant's memory, and it
cannot un-lose a fact that summarisation discarded three weeks ago.

---

## 7. What the failures jointly demand

Read as a set, the failures separate into five independent concerns. Independence matters:
each demands a distinct mechanism, and no one mechanism addresses more than its own column.

| Concern | Failures | Mechanism it demands |
| :-- | :-- | :-- |
| What enters the system | F8, F11 | Admission policy: extraction, typing, salience, PII gate |
| How it is represented | F5, F7, F4 | Typed facts with provenance, confidence, validity interval |
| What comes back | F3, F4, F8 | Multi-signal ranking, conflict resolution, budgeted injection |
| How it changes over time | F1, F6, F9 | Update, consolidation with citation, decay, deletion |
| Who may see it | F10, F11 | Index-level tenant partitioning, audit trail |

`first_principles.md` derives the required capabilities from the ground up rather than from
this table, and then checks that the two derivations agree. Where they disagree, the
disagreement is recorded as an open question.

---

## 8. Open questions raised by this analysis

1. Is extraction into typed facts strictly better than storing chunks, or does it trade F7
   for a new extraction-error failure mode? A fact extracted wrongly is worse than a chunk
   retrieved wrongly, because it looks authoritative. **Validation:** run both on the same
   transcript set in Deliverable 3 and compare error character, not just error rate.
2. Should supersession be inferred automatically, or should conflicting memories both be
   injected with their dates and the resolution left to the model? Automatic supersession is
   an irreversible write based on a fallible judgement.
3. What is the honest consistency window for deletion, given an asynchronous index? A number
   I can defend is better than a guarantee I cannot meet.
4. Does importance scoring at admission time justify its cost, given that importance is often
   only apparent in hindsight? `[VERIFIED]` Generative Agents scores importance at write time;
   `[INFERENCE]` that setting has no cost pressure comparable to a per-seat SaaS product.
5. Can any of this be evaluated without a human-labelled ground truth set, and if not, how
   large does that set need to be before the numbers mean anything?

---

## 9. Sources

Cited works, all from or consistent with the handbook's reference list (Appendix G).

1. Lewis, P., Perez, E., Piktus, A., et al. *Retrieval-Augmented Generation for
   Knowledge-Intensive NLP Tasks.* 2020. https://arxiv.org/abs/2005.11401
2. Park, J. S., O'Brien, J. C., Cai, C. J., et al. *Generative Agents: Interactive Simulacra
   of Human Behavior.* 2023. https://arxiv.org/abs/2304.03442
3. Packer, C., Wooders, S., Lin, K., et al. *MemGPT: Towards LLMs as Operating Systems.*
   2023. https://arxiv.org/abs/2310.08560
4. Vaswani, A., Shazeer, N., Parmar, N., et al. *Attention Is All You Need.* 2017.
   https://arxiv.org/abs/1706.03762
5. Liu, N. F., Lin, K., Hewitt, J., et al. *Lost in the Middle: How Language Models Use Long
   Contexts.* 2023. https://arxiv.org/abs/2307.03172 (not in Appendix G; added because it
   supplies the direct evidence against Approach E)

**AI assistance disclosure.** Claude was used to draft and pressure-test prose in this
document. The domain grounding, the choice of failure cases, the assumption decomposition,
and every `[VERIFIED]` / `[INFERENCE]` / `[ASSUMPTION]` boundary are mine and are what I will
defend in review. No benchmark number appears in this document because none has been measured.
