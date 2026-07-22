# Throughline

**The account memory layer for GTM agents.**

Plain-English overview of what this project is, what the assignment asks for, and why it is
worth your time beyond the grade. Written 19 July 2026, for you, not for the grader.

> **On the name.** *Throughline* is the connecting thread that runs through a story. That is
> literally what the system does: it carries the thread of an account relationship across
> sessions, across months, and across the handoffs where context normally dies. It also happens
> to describe what this project does for your career narrative.
>
> Alternates if you want something else: **Recall** (plainer, more generic), **Ledger** (fits
> your auditability theme but collides with the crypto wallet brand), **Carryover** (a real GTM
> term for pipeline crossing a quarter boundary, nice double meaning, but slightly negative
> connotation in sales).

---

## 1. The problem, in one paragraph

An AI assistant has no memory. Every conversation starts from zero. Tell it something on
Monday, and by Friday it is gone. Correct it, and the correction lasts exactly as long as the
browser tab. For a chatbot answering trivia that is fine. For an assistant helping an account
executive manage a relationship that runs eighteen months across dozens of calls, it is fatal,
because the entire value of the relationship *is* the accumulated context.

## 2. What that looks like concretely

The four failures that define the project. These are not hypothetical, they are what any
current system does today:

**The correction that never sticks.** The AE tells the assistant "Ravi left in March, Priya owns
this account now." Next session it says Ravi again. And the session after that. The AE stops
using it around the third time, because correcting it costs more than doing the prep manually.

**The fact that expired.** In February 2025 the buyer said "we're a Salesforce shop." In April
2026 they said "we finished the HubSpot migration." Ask a normal retrieval system what CRM they
use and it returns Salesforce, confidently, because that sentence is phrased more directly
on-topic and similarity search ranks *wording*, not *truth*. The system has no concept that a
fact can stop being true.

**The quote that means the opposite.** Stored snippet: "I don't think we need SSO for the
pilot." What actually happened: the buyer said that, the AE pushed back, and the buyer said "fair,
put it in, non-negotiable for prod." Retrieved alone, the snippet tells you the exact inverse of
the account's real position.

**The leak.** Two of your customers both sell to a company called Acme. Their notes look nearly
identical to a search engine. If customer A's private notes surface in customer B's account
brief, that is not a bug you apologise for. That is a company-ending event.

The first two are annoying. The last two are the ones that make this an engineering problem
rather than a prompt-tuning problem.

## 3. What we are building

A memory layer that sits between the conversation and the model, and makes five decisions the
model cannot make for itself:

| Decision | The question it answers |
| :-- | :-- |
| **Admission** | Should this even be remembered? (Not everything should. Some things legally must not be.) |
| **Representation** | Store it as *what*? A resolved fact with a date and a source, not a raw quote. |
| **Retrieval and ranking** | Which memories matter for *this* question, weighing relevance, recency, importance, and whether the fact is still valid. |
| **Injection** | Which of those fit in the token budget, and in what order. |
| **Lifecycle** | When does it get corrected, merged, expired, or deleted, and can we prove deletion actually happened. |

Plus two things underneath all of it: **tenant isolation** (no query path can even express a
cross-customer read) and **observability** (every one of the above decisions is logged, so when
the answer is wrong you can tell which stage failed).

**The one-line version for your outreach:** it is the difference between an assistant that has
read your account history and one that actually remembers it.

---

## 4. What the assignment actually asks

The handbook is called *Learning Through Reconstruction*. Its whole thesis is in the title: you
are not supposed to look up the right architecture and build it. You are supposed to
**reconstruct the pressures that made it necessary**, so the final design reads as a reasoned
response to constraints you personally hit rather than a pattern you copied.

That is why the eight deliverables are ordered the way they are:

| # | Deliverable | What it really tests |
| :-- | :-- | :-- |
| 1 | **Problem Reconstruction** | Can you explain why the obvious simpler solutions fail, before naming your solution? |
| 2 | **Weekly Research Scan** | Can you read papers and convert them into adopt / prototype / defer / reject decisions, not summaries? |
| 3 | **Productive Failure Baseline** | Will you build the naive version honestly and **measure** it failing, rather than asserting it would? |
| 4 | **System Design** | Does every component trace to a requirement or a measured failure? |
| 5 | **Genesis Workflow** | Can you run implementation as bounded, verifiable loops with recoverable state? |
| 6 | **Implementation + Verification** | Does it work, and can someone *other than the builder* prove it? |
| 7 | **Journal + Retrospective** | Can you show how your thinking changed, including where you were wrong? |
| 8 | **Transfer** | Can you adapt the principles to a domain you did not build in? |

**The standard that matters most:** "A working implementation is necessary but not sufficient."
A polished demo scores nothing without design rationale, measured failures, and independent
verification. That is unusual, and it is the reason this is worth doing properly.

**Status:** Deliverable 1 is done (4 artifacts in `reconstruction/`). Deliverables 2 through 8
are not started. Realistically about six more working sessions.

---

## 5. Why this is worth your time

This is the part that matters. Four reasons, strongest first.

### 5.1 You independently identified this as a market gap. In writing. Last week.

Open `../Deliverable-2/submission/market_research.pdf`, section 7, **Opportunity 2: Persistent
account memory across sessions and handoffs.** You wrote that no company in your 30-company
landscape sells this, while several sell conversation capture, which is the raw input to it.

You are now building the thing your own market research says is missing. That is not a
coincidence you engineered after the fact, it is the two tracks of this cohort converging, and
it is a genuinely strong thing to be able to say in an interview: *"I found the gap in my market
research, then I built it."*

### 5.2 It converts a weak portfolio line into your strongest one

Your knowledge base currently lists item **7b, Context-Aware LLM Memory Engine**, described as a
"project." Right now it is a description without numbers. After Deliverable 3 and 6 it becomes a
system with a measured baseline comparison, an adversarial evaluation set, tested tenant
isolation, and a verification report written by a separate reviewer.

That is the difference between "I built a memory module" and "I built a memory system, here is
what the naive version scored, here is what mine scored, here is the adversarial set, here is
the security report." One of those survives a technical interview.

### 5.3 It is the artifact your outreach campaign is missing

`outreach_campaign.md` message 3 is the teardown, and it is the highest-value message in the
sequence. It currently rests on the account research agent, which is honestly marked "eval
numbers still being finalised."

Throughline gives you a second, stronger artifact for that slot: a real system, with real
numbers, solving a problem you can demonstrate every one of those 30 companies has. And your
timing works. Deliverables 3 and 6 produce numbers well before your 3 October availability.

### 5.4 The skills map directly onto what these roles ask for

Straight from `market_research.pdf` section 5, the demanded clusters and where this project hits
them:

- **Retrieval, ranking, RAG** → the core of the system
- **LLM extraction** → the admission stage
- **Evals and observability** → Deliverables 6 and 10, and your research found these appearing as *requirements* now, not nice-to-haves
- **Multi-tenant data architecture, privacy, deletion** → the isolation and lifecycle work
- **Classical ML depth** → multi-signal ranking is a ranking problem, which is your six years

The one cluster it does *not* strengthen is GTM domain fluency, and that is what
`domain_primer.pdf` is for.

---

## 6. What makes it different from a RAG demo

Worth being clear about, because "I built a memory system with embeddings" is a crowded claim in
2026. Four things separate this from a weekend project, and all four are unglamorous:

1. **A measured baseline.** Most people describe why their approach is better. You will have run the naive version and have its numbers.
2. **Adversarial evaluation.** Superseded preferences, cross-tenant near-duplicates, PII, cold start. Not a happy-path demo.
3. **Deletion that is actually tested,** with a stated consistency window you can defend, rather than a delete call you assume worked.
4. **Independent verification.** Someone other than the builder confirming the claims.

Points 1 and 4 are the ones almost nobody has, and they map exactly onto your existing positioning:
*auditable, inspectable systems over black boxes.* This project is that thesis, built.

---

## 7. Honest risks

Not a sales document, so here is what could go wrong.

- **Scope.** The handbook's full spec is large. If time gets tight, the correct cut is depth over breadth: one excellent path through admission, ranking, injection, and deletion, with the non-goals documented, beats eight half-finished components. The non-goals are already written down in `reconstruction/problem_reconstruction.pdf` section 7.1 for exactly this reason.
- **The measurement trap.** Deliverable 3 needs real runs. If those get skipped or hand-waved, the whole chain collapses, because Deliverable 4's design and Deliverable 6's comparison both depend on those numbers. This is the single highest-risk step.
- **Typed extraction might be the wrong call.** Storing resolved facts instead of raw quotes fixes the SSO problem, but a wrongly extracted fact looks *authoritative* in a way a wrongly retrieved quote does not. This is written down as open question 1 and it gets settled by experiment in Deliverable 3, not by argument. If the experiment says I was wrong, the design changes.
- **Timeline.** About six sessions. Your last working day is 3 October. That is comfortable, but only if Deliverable 3 does not slip.

---

## 8. The elevator versions

**For a Head of AI, 15 seconds:**
> Most GTM assistants re-research the same account every session and cannot tell a current buyer
> preference from one that expired eighteen months ago. I built the memory layer that fixes
> that: admission control so it does not store everything, typed facts with validity dates so
> superseded preferences lose to current ones, and tenant isolation enforced below the retrieval
> API rather than as a filter.

**For your newsletter:**
> Everyone is building agents. Almost nobody is building the memory those agents need, and the
> hard part is not storage, it is deciding what deserves to be remembered and how long it stays
> true.

**For yourself, when it stops being fun:**
> This is the one portfolio piece that proves the thing I actually claim: that I build systems
> you can inspect, measure, and trust, not demos.

---

*Companion reading: `README.md` for repo structure and current status,
`reconstruction/problem_reconstruction.pdf` for the full argument,
`reconstruction/failure_analysis.md` for why the simpler designs break.*
