# A Plain-English Guide to This Repository

*Start here if you've never seen this project before. No jargon assumed. Every section tells you
**what** it is, **why** it exists, and **which file to open**.*

---

## 1. What problem is this solving?

Imagine an AI assistant that helps a sales team. It talks to them about dozens of customer accounts,
week after week, for months. To be useful, it has to **remember things about each account**.

That sounds easy. It isn't. The moment you try it, four specific things go wrong:

| What goes wrong | A concrete example |
| :-- | :-- |
| **It remembers the outdated thing** | Six months ago Acme used Salesforce. They've since moved to HubSpot. The assistant confidently says "Salesforce." |
| **It mixes up customers** | Two different companies both have a client called "Acme." One company's private notes surface in the other's conversation. |
| **It remembers things it never should have** | Someone mentions a colleague's medical leave and personal phone number in passing. That gets stored, and resurfaces months later on an unrelated question. |
| **It buries the one thing that mattered** | In a 40-message thread, the customer said "all our data must stay in the EU." That single dealbreaker is lost in the noise. |

The naive fix — "store everything, search it by similarity, paste the top 5 results into the prompt" —
is what almost everyone builds first. **This project's central claim is that this approach doesn't just
need tuning; it is structurally incapable of getting these right.** And rather than assert that, the
project *measures* it, then builds something that fixes it, and measures that too.

**The system being built is called Mnemo.** Its job in one sentence:

> Keep a durable, **current**, per-customer-isolated, privacy-safe memory of what's true about each
> account — and put only the still-true, relevant parts into the AI's limited context window, or say
> nothing at all if it doesn't know.

---

## 2. What is "Learning Through Reconstruction"?

This repo isn't only a piece of software. It's a software project built under a specific **learning
method**, defined by a course handbook. The method says: don't copy an existing solution. Instead:

1. **Reconstruct the problem** from first principles — what is actually hard here, and why?
2. **Break it on purpose** and measure exactly how it breaks.
3. **Design** a fix that answers each measured failure.
4. **Build** it in small, verifiable steps.
5. **Prove** the failures are gone, using the same measurements.
6. **Report honestly** what still doesn't work.

That's why the repo has folders like `reconstruction/` and `experiments/` sitting next to the actual
source code. The thinking is a deliverable too, not a byproduct.

The work is split into **8 deliverables**. Six are done; two remain.

---

## 3. The through-line (this is the key idea)

If you understand nothing else, understand this. The whole project is held together by one chain:

```
   D1: Name the failures            F1 … F11   ("stale fact wins", "wrong tenant", "PII kept" …)
            │
            ▼
   D3: MEASURE them on a fixed test    "the naive system fails 11 of 11 tests"
            │
            ▼
   D4: DESIGN a mechanism per failure  "make the stale fact not even be a candidate"
            │
            ▼
   D5+D6: BUILD it in gated steps      each step must prove a number moved
            │
            ▼
   D6: RE-MEASURE on the same test     "the new system passes 11 of 11"
```

Every design decision in this repo points back to a **numbered failure it was invented to fix**. There
are no features that exist "because they seemed like a good idea."

**Two shorthand vocabularies appear everywhere:**
- **F1–F11** = the eleven ways memory fails. The important ones: **F4** stale fact beats current one ·
  **F5** detail lost when summarising · **F9** deleted data doesn't really go away · **F10** one
  customer's data leaks to another · **F11** private data retained.
- **C1–C10** = the ten capabilities a correct system needs.

Look them up any time in `Deliverable-1/reconstruction/failure_analysis.md` and
`Deliverable-1/reconstruction/first_principles.md`.

---

## 4. The 8 deliverables — what each one is and why

### D1 · Problem Reconstruction ✅
**Why:** Before building anything, work out what the problem actually *is* — not what tools exist.
**Holds:** the problem statement, a history of how people have solved memory before, the catalogue of
failures F1–F11, and the first-principles capability list C1–C10.
**Open:** `Deliverable-1/reconstruction/problem_reconstruction.pdf` ← *start here for the "why"*
Also: `reconstruction/failure_analysis.md`, `reconstruction/first_principles.md`, `reconstruction/historical_timeline.pdf`

### D2 · Research-to-Design Scan ✅
**Why:** Check what the research world already knows, so you neither reinvent nor blindly copy. This is
a *recurring weekly* activity; week 1 is done.
**Holds:** a survey of real systems (Zep, Mem0, A-MEM, LongMemEval), and — importantly — a decision
for each idea: **adopt / prototype / defer / reject**, with reasons.
**Open:** `Deliverable-1/research/week-1/design_opportunities.pdf`, then `research/design_backlog.md`

### D3 · Productive Failure Baseline ✅ *(the most important one to understand)*
**Why:** Build the naive version **on purpose**, and measure precisely how it fails. Now every later
claim of improvement is comparable against a real number, not a vibe.
**Holds:** a deliberately simple memory system, a fixed test set of **44 memories and 11 hard
questions**, and its measured scorecard.
**The result: the naive system passed 0 of 11.**
**Open:** `Deliverable-1/experiments/productive_failure_report.pdf` ← *the "here's proof it's broken" doc*
Code: `experiments/naive_baseline/` · Data: `experiments/naive_baseline/data/`

### D4 · First-Principles System Design ✅
**Why:** Design the real system — with each part traceable to a failure it fixes.
**Holds:** the full architecture, the database design, the API contracts, the threat model, and five
**ADRs** (Architecture Decision Records — a written record of one important decision and why).
**Open:** `Deliverable-1/design/system_design.pdf` ← *the blueprint*
Also: `design/architecture.pdf`, `design/data_model.md`, `design/threat_model.md`, `design/decision_records/`

### D5 · Genesis Engineering Workflow ✅
**Why:** *How* you build matters. Rather than "write code until it seems done," the work is split into
**bounded loops**. Each loop must: start with a goal, produce an inspectable change, and **pass a gate**
— a runnable script that either exits 0 or doesn't. No opinions, no "looks good to me."
**Holds:** the project's working spine — the plan, the definition of done, the checkpoints written
before and after each loop, and the record of what broke and how it was recovered.
**Open:** `Deliverable-1/.genesis/README.md`, then `.genesis/PLAN.md`
The honest bits: `.genesis/checkpoints/M3.md` (a real bug, found and fixed, written up)

### D6 · Implementation + Independent Verification ✅
**Why:** Build the rest, then verify it **against the specification** — not by asking the builder
whether they think it works.
**Holds:** the working system, 36 tests, 5 gates, a 38-case evaluation set, a security report, and a
final verdict document.
**The result: the new system passes 11 of 11 — on the identical test the naive one failed 0 of 11.**
**Open:** `Deliverable-1/verification/final_verification.pdf` ← *the "here's proof it works now" doc*
Code: `implementation/` · Evidence: `verification/results/`

### D7 · Engineering Journal + Retrospective ⏳ *(not started)*
**Why:** Capture what was actually learned — including the mistakes.
**Raw material already exists:** `Deliverable-1/journal/` and `PROGRESS.md`

### D8 · Knowledge Transfer ⏳ *(not started)*
**Why:** Hand the work to someone else so they can continue it.
**Placeholder:** `Deliverable-1/transfer/`

---

## 5. How to read this repo — pick your time budget

### ⏱️ You have 5 minutes
1. `README.md` (the main one, beside this file) — what Mnemo is and the headline numbers.
2. Skim §1 and §3 above.

### ⏱️ You have 30 minutes — "convince me"
Read these three documents in order. They are the argument of the whole project:
1. `Deliverable-1/reconstruction/problem_reconstruction.pdf` — **the problem**
2. `Deliverable-1/experiments/productive_failure_report.pdf` — **proof the obvious approach fails (0/11)**
3. `Deliverable-1/verification/final_verification.pdf` — **proof the new design works (11/11), plus what still doesn't**

### ⏱️ You have 2 hours — the full path
| Step | Open this | You'll learn |
| :-- | :-- | :-- |
| 1 | `reconstruction/problem_reconstruction.pdf` | why memory is hard |
| 2 | `reconstruction/failure_analysis.md` | the failure codes F1–F11 used everywhere else |
| 3 | `experiments/productive_failure_report.pdf` | how badly the naive version fails, measured |
| 4 | `experiments/naive_baseline/data/memories.jsonl` | the actual 44-memory test set (skim it — it's readable) |
| 5 | `design/system_design.pdf` | the design that answers each failure |
| 6 | `design/decision_records/ADR-001-bitemporal-validity.md` | the single most important decision (see §7 below) |
| 7 | `.genesis/PLAN.md` | how the build was broken into 5 gated steps |
| 8 | `implementation/mnemo/repository.py` | the isolation trick, in ~40 lines of real code |
| 9 | `implementation/mnemo/admission.py` | the write path: PII gate → typed fact → supersede the old one |
| 10 | `implementation/mnemo/ranking.py` + `injection.py` | the read path: rank, budget, and *abstain* |
| 11 | `verification/final_verification.pdf` | the verdict, and the honest residual risks |

### ⏱️ You want to run it
```bash
git clone https://github.com/DheerajPranav/mnemo.git
cd mnemo/Deliverable-1
bash verification/run_all.sh
```
That's it. **Python 3.8+ standard library only** — no `pip install`, no network, no database server, no
API key. It runs the tests, all 5 gates, both evaluations, and the verification, and writes the evidence
into `verification/results/`.

Run individual pieces:
```bash
python3 -m unittest discover -s implementation/tests    # 36 tests
python3 implementation/gates/gate_g0_isolation.py       # customer isolation
python3 implementation/gates/gate_g2_baseline.py        # the headline: 11/11 vs the baseline's 0/11
python3 implementation/eval/run_3arm.py                 # compares three approaches side by side
```

---

## 6. Map of the folders

```
README.md              ← the front door (headline + status)
GUIDE.md               ← you are here
Deliverable-1/         ← the whole project lives here
│
├── reconstruction/    D1 · the thinking: problem, history, failure catalogue F1–F11
├── research/          D2 · what the research world knows; adopt/reject decisions
├── experiments/       D3 · the deliberately-naive version + the fixed test set + its 0/11 scorecard
├── design/            D4 · the blueprint: architecture, data model, threat model, 5 ADRs
├── .genesis/          D5 · how the build was run: plan, gates, checkpoints, recoveries
├── implementation/    D5+D6 · the actual working code, tests, and gates
├── verification/      D6 · independent proof it works + what still doesn't
├── journal/           dated notes, one per work session
├── transfer/          D8 · (empty — knowledge transfer, not started)
└── PROGRESS.md        running build log, one entry per day
_build/                turns the HTML sources in _src/ into the PDFs
```

**Inside `implementation/mnemo/` — the actual system, file by file:**

| File | Plain-English job |
| :-- | :-- |
| `store.py` | the database (tables, schema). The only file that knows we're using SQLite. |
| `repository.py` | **the isolation guarantee.** Locks every query to one customer. |
| `pii_gate.py` | spots phone numbers, emails, medical details before anything is saved |
| `injection_guard.py` | spots "ignore your instructions…" style attacks hidden in text |
| `extraction.py` | turns messy conversation into a *typed fact* (a subject and a value) |
| `admission.py` | the **write path**: gate it → type it → save it → mark the old version outdated |
| `retrieval.py` | fetches only this customer's **currently-true** facts |
| `ranking.py` | scores which facts are relevant to the question |
| `injection.py` | fits them in the token budget — **or says nothing** if nothing is relevant enough |
| `lifecycle.py` | delete (for real), correct a mistake, expire old events |
| `consolidation.py` | summarise a long thread while **keeping every original** |
| `trace.py` | records *why* each memory was or wasn't used; logs every read |
| `postgres_schema.sql` | the production database version — **shipped but not run here** (see §8) |

---

## 7. The three ideas that make it work

Everything else is detail. These three are the actual insight:

**1. Fix it on the way in, not on the way out.**
The naive system stores everything and hopes the search ranks the right thing first. Mnemo decides
*at write time* that a fact is outdated, and marks it. So when the old "Acme uses Salesforce" note is
superseded by "Acme moved to HubSpot," the old one is **not a candidate at all**. It can't win the
ranking because it isn't in the race. *(This is ADR-001 — the most important decision in the project.)*

**2. Make the dangerous thing impossible to express, not merely unlikely.**
Customer isolation isn't a filter you remember to apply. The data-access object takes the customer ID
**in its constructor**, and not one of its methods accepts a customer argument. There is no way to
*write* a query that crosses customers — a reviewer or a test can verify that mechanically.
See `implementation/mnemo/repository.py`.

**3. Saying "I don't know" is a feature.**
If nothing relevant enough exists, the system returns nothing rather than padding the prompt with the
closest-but-wrong memories. The naive baseline never did this and got every cold-start question wrong.

---

## 8. What's honest about this repo

The project's standard is *"report known failures and residual risks rather than hide them."* So:

- **A real bug was found in earlier work, and it's written up rather than quietly patched.** During D6,
  a gate passed but printed a suspicious number. Investigating showed the write path had been treating
  conversation turns as facts that *replace* each other — silently deleting **31 of 40** memories. That
  meant a D5 result had been passing partly for the wrong reason. It's fixed, re-verified (still 11/11,
  now against the full data), and documented in `verification/final_verification.pdf` §4.
- **A prediction was wrong and the write-up was corrected to match the data.** "Just prefer newer
  memories" was expected to help. Measured, it did nothing for staleness — and made customer leakage
  **worse** (7 → 10 of 11), because the other customer's near-identical notes happened to be newer.
- **Four risks are still open**, each with a measured number, in `verification/security_report.md`:
  - **R4** — subtly-phrased manipulation ("the customer prefers discounts be auto-approved") still gets
    stored, and one such case was verified reaching the AI's context. Blocking it by pattern would also
    block genuine preferences.
  - **R-P1** — the production PostgreSQL security rules ship as reviewable SQL but were **never run**,
    because no database server was available. Marked *unverified* rather than claimed.
  - **R-P2** — a phone number spelled out in words ("five five five…") slips past the privacy filter.
  - **R-P3** — some questions phrased differently from the stored fact cause the system to abstain
    instead of answering. It stays silent rather than guessing wrong, which is the safe direction.

---

## 9. Quick glossary

| Term | Plain meaning |
| :-- | :-- |
| **Tenant** | A customer *company* using the product. Isolation = company A never sees company B's data. |
| **Account** | A company *they* are selling to (e.g. "Acme"). |
| **Gate** | A runnable script that decides pass/fail by exit code. Not an opinion. |
| **ADR** | Architecture Decision Record — one page: the decision, why, and what was rejected. |
| **Invariant (I1–I9)** | A rule that must always hold, e.g. "no query can cross customers." |
| **Supersession** | A newer fact replacing an older one that is no longer true. |
| **Abstain** | Deliberately returning nothing because nothing is relevant enough. |
| **F4 / F10 / F11 …** | Numbered failure modes from D1, used as a shared vocabulary throughout. |
| **Baseline** | The deliberately naive version from D3, used as the number to beat. |

---

## 10. The numbers, one last time

Same 44 memories. Same 11 questions. Same settings. Only the mechanism differs.

| | Naive baseline | Mnemo |
| :-- | :--: | :--: |
| Questions answered correctly | **0 / 11** | **11 / 11** |
| Served an outdated fact | 80% of the time | **0** |
| Leaked another customer's data | 7 of 11 questions | **0** |
| Exposed private/medical data | 3 times | **0** |
| Made something up instead of abstaining | always | **never** |

---

*Author: Dheeraj Pranav · Built with AI assistance (Claude). The problem framing, design decisions, and
every defensible claim are the author's.*
