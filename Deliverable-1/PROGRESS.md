# PROGRESS — Throughline / Conversational Memory Intelligence System

Running process log for the *Learning Through Reconstruction* handbook build.
One section per work day. Newest day at the top of the day list.

- **Repo:** `Deliverable-1/` (the whole project; 8 handbook sub-deliverables live in its subfolders)
- **Handbook:** `../deliverable_1.pdf` (v1.0, June 2026)
- **Author:** Dheeraj Pranav
- **This run's scope:** Day 1 = verify/polish Deliverable 1 · Day 2 = Deliverable 2 (Research-to-Design Scan) · Day 3 = Deliverable 3 (Productive Failure Baseline)

> Convention: this log records *what was done, decisions made, commands run, and blockers*.
> It is deliberately terse. The narrative reasoning for each session lives in `journal/YYYY-MM-DD.md`.

---

## Tooling setup (2026-07-22, pre-Day-1)

Installed the Genesis / agent-swe-kit stack per `../tools/genesis-kit` instructions.

| Component | Location | Status |
| :-- | :-- | :-- |
| genesis-kit | `../tools/genesis-kit` (already cloned) | ✅ installed via `./install.sh` |
| agentic-swe-kit wiki | `~/.agentic-swe-kit/wiki` (7 domains) | ✅ |
| agentic-swe-kit skills | `~/.hermes/skills/{swe-foundations,mlops}` + mirrored to `~/.claude/skills` | ✅ |
| genesis skill | `~/.claude`, `~/.hermes`, `~/.codex` `/skills/genesis` | ✅ |
| env vars | `GENESIS_KIT_ROOT`, `AGENTIC_SWE_WIKI_ROOT` → `~/.zshrc` | ✅ |

Commands run:
```bash
brew install poppler                       # to read the handbook PDF (pdftotext)
cd ../tools/genesis-kit && ./install.sh    # clones + installs agentic-swe-kit, drops genesis skill
cp -R ~/.hermes/skills/{swe-foundations,mlops} ~/.claude/skills/   # mirror swe skills for Claude Code
```

Note: the agentic-swe-kit installer targets `~/.hermes/skills` only; mirrored into `~/.claude/skills`
so the `agentic-swe-master` orchestrator + domain skills are discoverable in Claude Code too.

The Genesis *spine* (`.genesis/` scaffold) is **not** initialised yet — by handbook §7.2 it is
initialised only after the system design (Deliverable 4) has a stable first version. That is
Deliverable 5, a later run. Prep/install done now.

---

## Day 1 — 2026-07-22 — Verify / polish Deliverable 1 (Problem Reconstruction)

**Goal:** independent verification pass over the already-complete Deliverable 1 (maker ≠ checker),
plus any low-risk polish. D1 was authored 19 July 2026 (previous session).

**Status:** ✅ **DONE** — verdict **PASS** (Proficient-to-Exceptional).

Artifacts reviewed (all in `reconstruction/`): `problem_reconstruction.pdf`,
`historical_timeline.pdf`, `failure_analysis.md`, `first_principles.md`.

**What I did:**
- Read all four D1 artifacts + handbook §3.2/§3.3/Appendix A/§11, and checked D1
  requirement-by-requirement (all present — see verification report §2).
- Wrote `reconstruction/deliverable1_verification.md` (independent verification + quiz-me gate).
- Wrote Day 1 journal → `journal/2026-07-22.md`.

**One defect found + fixed (polish):** evidence-tag scheme was inconsistent — the two `.md`
docs used 4 tags (`verified/inference/assumption/to measure`), the two PDFs only 3. Unified to
4 across all four artifacts:
```
# added .tag.tomeasure to ../_build/print.css
# edited _src/problem_reconstruction.html (callout + §6.1) and _src/historical_timeline.html (table)
../_build/topdf.sh _src/problem_reconstruction.html reconstruction/problem_reconstruction.pdf
../_build/topdf.sh _src/historical_timeline.html   reconstruction/historical_timeline.pdf
```
Presentation-only change; no claim/number/source altered. Verified `to measure` renders in both PDFs.

**Non-blocking recommendations** left for the author (verification report §5): optional table-caption
note on non-chronological era grouping; optional cross-reference tying the three open-question lists.

**Decisions:** applied the tag fix (Communication win, tightens D1→D3 link) but did **not**
re-argue any content (maker owns the argument; verifier flags, doesn't overwrite).

---

## Day 2 — 2026-07-22 — Deliverable 2: Weekly Research-to-Design Scan

**Status:** ✅ **DONE.**

**Artifacts produced (all required §4 artifacts + ADRs):**
- `research/research_landscape.md` — maintained component map (C1–C10 × sources × tracked recent work)
- `research/design_backlog.md` — durable adopt/prototype/defer/reject backlog (B-001…B-013)
- `research/week-1/component_scan.md` — glimpse across components, targeting the 4 weakest
- `research/week-1/idea_evaluation_matrix.md` — shortlist matrix with per-idea justification
- `research/week-1/challenge_notes.md` — §4.3 challenge (lead: *Back to Basics* 2604.11628) + position changes
- `research/week-1/design_opportunities.pdf` — the 20-min design review (rendered)
- `design/decision_records/ADR-001/002/003` — bi-temporal validity · eval scaffold · PII gate

**Sources web-verified before citing:** Zep 2501.13956, Mem0 2504.19413, A-MEM 2502.12110,
LongMemEval 2410.10813, Back-to-Basics 2604.11628.

**Headline decisions:** ADOPT bi-temporal validity (move conflict resolution off the ranker) ·
ADOPT LongMemEval eval scaffold · ADOPT Presidio PII gate · PROTOTYPE Mem0 op-selector ·
DEFER A-MEM linking · REJECT A-MEM evolution / LLMLingua / SISA-analogy.

**Feeds Day 3:** 3-arm retrieval comparison (naive / +recency / validity-filter), a *strong*
baseline retriever (not a straw man), and an eval set on the LongMemEval scaffold + GTM cases.

---

## Day 3 — 2026-07-22 — Deliverable 3: Productive Failure Baseline

**Status:** ✅ **DONE.**

**Goal / definition of done (handbook §5):** runnable `experiments/naive_baseline/`,
`experiments/baseline_protocol.md`, `experiments/baseline_results.csv`,
`experiments/productive_failure_report.pdf`, `experiments/error_examples.jsonl`. Fixed seeded
dataset covering all six required workload conditions (irrelevant/contradictory memories;
preferences that change over time; long conversations w/ constrained budget; multiple users w/
similar info; sensitive info that should not be retained; cold-start/no-relevant). Measured — not
asserted — failures, mapped to F1–F11 and replacing D1 `to measure` tags with numbers.

**Artifacts produced (all five required §5 artifacts):**
- `experiments/naive_baseline/` — pure-stdlib code: `build_dataset.py` (seeded dataset,
  `SEED=20260722`), `baseline.py` (TF-IDF cosine, no filtering), `evaluate.py` (measures every
  failure), `data/{memories,queries}.jsonl` (committed), `README.md`, `metrics.json`
- `experiments/baseline_protocol.md` — pre-registered method, metric definitions, threats to validity
- `experiments/baseline_results.csv` — per-query rows + aggregate block
- `experiments/error_examples.jsonl` — 11 concrete failures with retrieved evidence
- `experiments/productive_failure_report.pdf` — Appendix D report (rendered from
  `_src/productive_failure_report.html`); also updated `experiments/README.md` (Not started → Complete)

**Commands run:**
```bash
cd experiments/naive_baseline && python3 build_dataset.py && python3 evaluate.py
../../../_build/topdf.sh _src/productive_failure_report.html experiments/productive_failure_report.pdf
```

**Measured headline (0/11 pass; every number machine-produced by `evaluate.py`):**
| Metric | Value |
| :-- | :-- |
| overall_accuracy | 0.000 (0/11) |
| recall_at_k | 0.333 (3/9) |
| supersession_failure_rate (F4) | 0.800 (4/5) |
| inversion_failures (F7) | 1 (gold @ rank 31) |
| cross-tenant leak — F10-probed / **all queries** | 0.500 / **7 of 11** |
| pii_exposure_count (F11) | 3 |
| coldstart_abstention_failure_rate | 1.000 (2/2) |
| wasted_topk_slot_rate (F8) | 0.556 (25/45) |
| avg / max injected tokens | 92.1 / 105 (budget never bound) |
| latency p50 / p95 | 0.042 / 0.047 ms |

**Decisions:** lexical TF-IDF (stdlib, reproducible; `pip` blocked by PEP 668) over a dense embedder
— justified because the hypothesis is about what similarity *cannot express*, not signal quality
(protocol §2.1/§8). Condition-appropriate pass/fail, not one global accuracy. Retrieval-only scope
stated explicitly: F1/F2/F5/F6/F9 out of scope (need write path / summariser / deletion test) →
deferred to Deliverable 6.

**Retired two D1 `to measure` tags to numbers:** wasted-slot proportion (D-3) → **0.556**;
single-signal supersession failure (D-1/B-3) → **0.80**. Reproduced 2 of D1's 5 *unrecoverable*
failures (F10, F11) — sufficient to reject store-everything single-signal retrieval for a
multi-tenant regulated setting. Honest non-confirmation: F3 buried-fact did **not** reproduce (lexical
signal surfaced the dealbreaker at rank 1); reported as such.

**Hypothesis:** supported. Failures are structural (gold at rank 31 while stale/foreign at rank 1–2;
a better embedder makes F10 *worse*), not fixable by re-ranking or more budget.

---

## Day 4 — 2026-07-22 — Deliverable 4: First-Principles System Design

**Status:** ✅ **DONE.** All 8 §6.2 artifacts complete. Approach: spine-first + mid-point steer
(Dheeraj confirmed the 5 load-bearing decisions), then finished the remaining 3.

**Envelope:** **small/team B2B SaaS** (~2×10⁶ facts, single region) — deliberate downscale from D1 §4.

**Artifacts produced (all 8, handbook §6.2):**
- `design/system_design.pdf` — all 11 §6.2 sections; every component cites C/P/F; milestones + gates
- `design/architecture.pdf` — component diagram (write/read paths, 2 trust boundaries) + traceability matrix
- `design/data_flow.pdf` — admit/retrieve sequences, op-selector decision tree, deletion cascade, consolidation
- `design/data_model.md` — Postgres schema; every field cites a capability/failure
- `design/api_contracts.md` — admit/retrieve/lifecycle/deletion/trace/eval; tenant-ambient invariant
- `design/threat_model.md` — 5 assets, 2 trust boundaries, 6 STRIDE threats, residual register (R1–R6)
- `design/decision_records/` — ADR-001…005 (added ADR-004 envelope, ADR-005 single-store)
- `design/sprint_plan.md` — S0–S4, risk/dependency-ordered, each ending on an acceptance gate
- also updated `design/README.md` (Not started → Complete)

**Commands run:**
```bash
../../_build/topdf.sh _src/system_design.html design/system_design.pdf
../../_build/topdf.sh _src/architecture.html   design/architecture.pdf
../../_build/topdf.sh _src/data_flow.html      design/data_flow.pdf
```

**Five load-bearing decisions (confirmed by Dheeraj):** (1) small/team envelope ~2×10⁶ facts (ADR-004);
(2) single Postgres + pgvector, index as derived projection → deletion window collapses to a txn
(ADR-005); (3) isolation via RLS + constructor-scoped repository (no method can express cross-tenant
read); (4) conflict resolution on the write path (ADR-001), ranker orders only valid facts;
(5) hand-specified 4-signal ranker, op-selector kept as *prototype* (cost unproven, R6).

**New this deliverable:** threat **T4/R4 memory-borne prompt injection** — the store is an indirect-
injection channel; typed extraction defangs most, but it's v1's open frontier (D6 red-team). A concern
D1's failure-driven method could not have surfaced.

**Feeds:** D5 (sprint gates G0–G4 → Genesis BUILD-loop checkpoints; acceptance tests → checker oracle)
and D6 (implementation + verification).

**D2 note:** week-1 is a complete instance of the *recurring* Weekly scan; not manufacturing a week-2
now — resume on the next real cycle, targeted by D4's least-certain component (op-selector cost).
