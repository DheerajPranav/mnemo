# Conversational Memory Intelligence System

Repository for the *Learning Through Reconstruction* AI Engineering Handbook (v1.0).

**Author:** Dheeraj Pranav
**Grounding domain:** GTM AI, B2B SaaS revenue teams
**Status as of 19 July 2026:** Deliverable 1 complete. Deliverables 2 to 8 not started.

---

## What this system is

A memory layer for a GTM assistant used by revenue teams inside a B2B SaaS vendor. It decides
what conversational information should be retained, represents and stores it safely, retrieves
and ranks relevant memories, injects them into model context under a token budget, and manages
consolidation, decay, observability, and tenant isolation.

The handbook specifies the system generically. I have grounded it in GTM because that domain
supplies naturally adversarial conditions rather than contrived ones: near-duplicate entities
across tenants, preferences with real expiry dates, regulated personal data arriving
incidentally, and an isolation requirement with commercial consequences. It is also the domain
of my last six years of production work.

---

## Current status

| # | Deliverable | Status | Artifacts |
| :-- | :-- | :-- | :-- |
| 1 | Problem Reconstruction | **Complete** | 4 of 4 |
| 2 | Weekly Research-to-Design Scan | Not started | `research/` |
| 3 | Productive Failure Baseline | Not started | `experiments/` |
| 4 | First-Principles System Design | Not started | `design/` |
| 5 | Genesis Engineering Workflow | Not started | `.genesis/` |
| 6 | Implementation and Verification | Not started | `implementation/`, `verification/` |
| 7 | Journal and Retrospective | Not started | `journal/` |
| 8 | Knowledge Transfer and Contribution | Not started | `transfer/` |

Empty directories are placeholders matching the handbook's required top-level structure. Each
carries a `README.md` stating what it will hold and which deliverable fills it. Nothing in this
repository claims completeness it does not have.

---

## Deliverable 1: Problem Reconstruction

Four artifacts, all in `reconstruction/`.

| Artifact | What it does |
| :-- | :-- |
| [`problem_reconstruction.pdf`](reconstruction/problem_reconstruction.pdf) | The main document. Problem stated without naming a solution, actors, constraint envelope, prior approaches, failure evidence, derived requirements, open questions. Follows handbook Appendix A. |
| [`historical_timeline.pdf`](reconstruction/historical_timeline.pdf) | Nine eras from implicit model context to managed conversational memory, each as `approach -> observed bottleneck -> next approach`. |
| [`failure_analysis.md`](reconstruction/failure_analysis.md) | Five prior approaches broken down into their load-bearing assumptions, with worked failure traces and an eleven-row failure taxonomy. |
| [`first_principles.md`](reconstruction/first_principles.md) | Ten capabilities derived forwards from eight premises about the setting, cross-checked against the failure-driven list, with falsification conditions. |

### The argument in one paragraph

A model is a pure function of its context, so nothing persists unless something writes it down.
Context is finite, monotonically costly, and position-sensitive, so injection is a constrained
selection problem rather than a copying problem. Conversation is a low-precision,
high-redundancy source containing information that is sometimes ineligible for retention, so
there must be an admission decision. Facts have validity intervals and the world revises them,
so a memory is a proposition plus a time interval plus a supersession relation. Tenants are
mutually distrusting and share infrastructure, so isolation is an invariant rather than a
filter. Together these force ten capabilities that no simpler design provides, and that a
larger context window does not provide at any size.

### Read them in this order

1. `problem_reconstruction.pdf` for the whole argument
2. `failure_analysis.md` for why simpler designs break, worked out concretely
3. `first_principles.md` for the forwards derivation and where the two derivations disagree
4. `historical_timeline.pdf` for how the field arrived here

---

## Evidence conventions

Every claim carries one of four tags, used consistently across all four artifacts.

| Tag | Meaning |
| :-- | :-- |
| `[VERIFIED]` | Stated in a cited paper, or in my own production experience, with the source named. |
| `[INFERENCE]` | My reading of what the evidence implies for this system. Not claimed by the source. |
| `[ASSUMPTION]` | A working assumption about my deployment setting. Unmeasured. |
| `[TO MEASURE]` | A claim I refuse to assert until the Deliverable 3 baseline produces a number. |

**No benchmark result appears anywhere in this repository yet.** The naive baseline is
Deliverable 3 and has not been built. Every constraint target in
`problem_reconstruction.pdf` section 4 is a target I set to design against, not a measurement.

---

## Two things I would most like challenged

**1. Observability and evaluation are invisible to failure-driven analysis.** Capabilities C9
(decision observability) and C10 (offline evaluation) do not appear anywhere in the
failure-driven derivation. They arrive only from the forwards derivation. Breaking prior
designs surfaces the failures those designs can *exhibit*, never the failures I would be unable
to *detect*. If that reasoning is wrong, the case for deriving requirements in both directions
weakens considerably.

**2. Typed extraction may trade one failure for a worse one.** Storing resolved claims instead
of raw chunks fixes the out-of-context inversion problem, but a wrongly extracted fact looks
authoritative in a way a wrongly retrieved chunk does not. This is open question 1 and it is
settled empirically in Deliverable 3, not by argument.

---

## Building the PDFs

Sources are in `_src/` as HTML. Rendered with headless Chrome via the shared script:

```bash
../_build/topdf.sh _src/problem_reconstruction.html reconstruction/problem_reconstruction.pdf
../_build/topdf.sh _src/historical_timeline.html   reconstruction/historical_timeline.pdf
```

The shared stylesheet is `../_build/print.css`. Editing an HTML source and re-running the
script is the only build step.

---

## AI assistance disclosure

Claude was used to draft prose, check the historical chain for gaps, and pressure-test the
derivation in all four artifacts. The domain grounding, the choice of failure cases, the
premise and assumption decomposition, the constraint targets, the falsification conditions,
and every verified / inference / assumption boundary are mine and are what I will defend in
review. Per the handbook's accountability rule, I am responsible for every claim here
regardless of which tool produced the first draft.
