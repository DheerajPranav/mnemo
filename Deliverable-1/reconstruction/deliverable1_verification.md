# Independent Verification — Deliverable 1: Problem Reconstruction

**Verifier role:** maker ≠ checker pass, run against the handbook specification rather than
against the author's own summary (handbook §11, principle 6; §8.2 verification discipline
applied early).
**Date:** 22 July 2026
**Artifacts verified:** the four required Deliverable 1 artifacts as they stood after the
19 July authoring session, plus the two consistency edits recorded in §4 below.

> This is a verification of Deliverable 1 *only*. It does not assert anything about the system's
> implementation, which does not exist yet. Its job is to answer one question: **could another
> engineer, who has not seen the target architecture, use these four documents to explain why
> the system is needed, which simpler designs fail, and what requirements follow — with claims
> backed by sources, experiments, or clearly-labelled assumptions?** (handbook §3.3 completion
> standard.)

---

## 1. Verdict

**PASS — meets the handbook completion standard; quality sits at Proficient-to-Exceptional.**

The four artifacts collectively satisfy every required content item in handbook §3.3, follow the
§3.2 process, and instantiate the Appendix A template in full. The argument is reconstructive
rather than copied: each derived capability is traced back to a specific bottleneck or measured
failure mode, and the two independent derivations (failure-driven and first-principles) are
reconciled explicitly, with their one genuine disagreement surfaced rather than smoothed over.

No non-negotiable gate (handbook §11.2) is in scope for Deliverable 1, so none is at risk here.
The gates that *this* deliverable sets up for later — baseline comparison, isolation, deletion —
are correctly deferred and explicitly flagged `to measure` / `assumption`.

---

## 2. Requirement-by-requirement check

### 2.1 Handbook §3.2 — required process

| Process step | Met? | Evidence |
| :-- | :-- | :-- |
| Write the problem without naming the intended solution | ✅ | `problem_reconstruction` §1 is solution-free by construction — no mention of memory, retrieval, embeddings, or storage. Verified by reading: the words first appear in §5 (prior approaches). |
| Historical chain: implicit context → external memory → retrieval augmentation → managed memory | ✅ | `historical_timeline` — 9 eras, `<2014` hidden-state → 2014-15 external memory → 2017 attention → 2020 RAG → 2022 in-model retrieval → 2017-18 ANN indexes → 2023 Generative Agents → 2023 MemGPT → 2023+ long context → 2026 managed memory. |
| At least three previous or simpler approaches | ✅ (5) | `failure_analysis` Approaches A–E: stateless, full replay, rolling summarisation, single-signal RAG, long-context-as-memory. Over-satisfied. |
| For each approach: assumptions + a constructed failure case | ✅ | Each of A–E has an explicit load-bearing-assumption decomposition and ≥1 worked failure trace (A-1/A-2, B-1/B-2/B-3, C-1/C-2, D-1…D-6, E). |
| Derive the minimum capabilities a better system needs | ✅ | `first_principles` C1–C10, derived forwards from 8 premises, then cross-checked against the failure list. |

### 2.2 Handbook §3.3 — required contents

| Required content | Met? | Where |
| :-- | :-- | :-- |
| Precise problem statement, affected users, consequences | ✅ | `problem_reconstruction` §1 (statement), §2.2 (5-actor table incl. the non-user buyer/data-subject), §3 (consequences ordered by recoverability). |
| Constraints: token budget, latency, cost, privacy, correctness, multi-user isolation | ✅ (all 6) | `problem_reconstruction` §4 table: Context (≤2k/16k), Latency (p95≤300ms), Cost (≤15%), Privacy (deletion ≤60s/≤24h), Isolation (zero cross-tenant), Correctness (beat baseline). Mirrored in `first_principles` §4. |
| Timeline: approach → observed bottleneck → next approach | ✅ | `historical_timeline` — every era uses the literal *Bought / Hit / Forced* structure; compressed table restates it as approach / bottleneck / what-it-forced. |
| Concrete failure cases + supporting evidence | ✅ | `failure_analysis` — 11-row taxonomy F1–F11, each traced to a violated assumption; evidence via Liu et al. (Lost in the Middle), Park et al. (Generative Agents), Lewis et al. (RAG), plus labelled production experience. |
| First-principles derivation of required capabilities | ✅ | `first_principles` §1–§2 (premises P1–P8 → capabilities C1–C10), §3 (bidirectional cross-check, no orphans). |
| Unresolved questions that shape the design | ✅ | `problem_reconstruction` §8 (5 Qs), `failure_analysis` §8 (5 Qs), `first_principles` §6 (5 falsification conditions). |

### 2.3 Required artifacts present

| Artifact | Present | Note |
| :-- | :-- | :-- |
| `reconstruction/problem_reconstruction.pdf` | ✅ | Rendered from `_src/problem_reconstruction.html`. |
| `reconstruction/historical_timeline.pdf` | ✅ | Rendered from `_src/historical_timeline.html`. |
| `reconstruction/failure_analysis.md` | ✅ | |
| `reconstruction/first_principles.md` | ✅ | |

### 2.4 Appendix A template — all 8 items instantiated

Problem ✅ · Importance ✅ · Constraints ✅ · Prior approaches ✅ · Failure evidence ✅ ·
Historical chain ✅ · Derived requirements ✅ · Open questions ✅.

---

## 3. What is genuinely strong (defensibility notes)

These are the parts that lift the work above "complete" and that would survive a technical
challenge:

1. **Bidirectional derivation with a recorded disagreement.** `first_principles` §5 does the
   thing most reconstructions skip: it notes that C9 (observability) and C10 (offline eval)
   are *not* discoverable from breaking prior designs — a failure-driven method can only surface
   failures a design can *exhibit*, never failures you would be unable to *detect*. That is a
   real finding about method, and it is the single most defensible claim in the deliverable.
2. **The unrecoverable-failure lens drives the architecture.** `failure_analysis` §6 marks 5 of
   11 failures unrecoverable (F5, F6, F9, F10, F11) and §7 uses exactly those to justify which
   invariants exist. This is why isolation and deletion are treated as invariants, not features
   — and it maps cleanly onto the handbook's own non-negotiable gates.
3. **Constraints are honest.** Every number in §4 is tagged `assumption` with a stated basis and
   an explicit "none is measured, all revisable" preface. Nothing is dressed as a result.
4. **Non-goals are written down before design starts** (`problem_reconstruction` §7.1,
   `first_principles` §7), which is what stops Deliverable 4 from quietly expanding.

---

## 4. Change applied during verification (polish)

One consistency defect was found and fixed. It is the only substantive edit made in this pass.

- **Finding.** The two Markdown artifacts use a **four-tag** evidence scheme
  (`verified` / `inference` / `assumption` / `to measure`); the two PDFs defined only **three**
  and handled pending-measurement claims in prose ("marked as pending rather than estimated").
  The scheme was therefore not uniform across the four artifacts — a Communication-dimension
  nick, and it slightly weakened the D1→D3 through-line (the `to measure` items are exactly what
  the Day 3 baseline resolves).
- **Fix.**
  - Added `.tag.tomeasure` to `../_build/print.css`.
  - `problem_reconstruction.html`: rewrote the "Evidence standard" callout to define all four
    tags as one scheme; applied `to measure` to the illustrative cosine scores in §6.1.
  - `historical_timeline.html`: tagged the "to be established by the Deliverable 3 baseline"
    cell `to measure`.
  - Re-rendered both PDFs via `../_build/topdf.sh`.
- **Why this is safe.** It changes presentation and labelling only; no claim, number, source, or
  argument was altered. It makes the four artifacts state one scheme instead of two.

---

## 5. Minor observations (non-blocking, author's call)

Recorded for completeness; none affects the PASS verdict. Left for the author to accept or reject.

1. **Compressed-chain table ordering** (`historical_timeline`): the FAISS/HNSW row (2017-18) sits
   after the RETRO row (2022) because eras are grouped thematically (retrieval-mechanism vs.
   index-scale). The "Honest caveat" already discloses that eras were concurrent, so this is
   defensible; a reader skimming only the table might briefly read it as a date error. Optional:
   add "(grouped by theme, not strictly chronological)" to the table caption.
2. **`Lost in the Middle` provenance.** Correctly disclosed as outside handbook Appendix G in both
   documents that cite it. Good practice; no change needed.
3. **Open-question numbering differs slightly** across `problem_reconstruction` §8,
   `failure_analysis` §8, and `first_principles` §6 (they are related but not a single shared
   list). This is fine — they are three views — but a one-line note that OQ-1 (typed extraction
   risk) is the common thread would help a reader connect them. Optional.

---

## 6. Defensibility check (Genesis quiz-me gate, applied to D1)

Per the handbook's anti-rubber-stamp discipline, three questions the author should be able to
answer without notes. These are the ones a design reviewer is most likely to press:

1. **Design decision:** Why is isolation stated as "no query path can express a cross-tenant read"
   rather than "every query path filters by tenant"? *(Expected: the weak form fails on both
   safety — a missed filter leaks — and quality — foreign memories consume top-k slots before
   being discarded, so recall degrades even when nothing leaks. See `first_principles` C8.)*
2. **Edge case:** A buyer says "I don't think we need SSO for the pilot," then later concedes
   "put it in, non-negotiable for prod." What must the storage unit be, and why does better
   retrieval not fix this? *(Expected: the unit must be an extracted, typed, resolved claim, not
   a chunk; the failure is representational, independent of ranking. `failure_analysis` D-2.)*
3. **Change impact:** If the Day 3 baseline resolves superseded preferences correctly from
   recency cues alone, which capability's justification collapses, and what happens to the design?
   *(Expected: `first_principles` §6 falsifier 1 — P4 would not force C5 in practice, and
   multi-signal ranking would not be earning its cost; the ranking complexity gets cut.)*

If any of these cannot be answered cleanly, the verdict for that thread downgrades to UNCERTAIN
and the relevant section is reopened. On the documents as written, all three are answerable from
the text.

---

## 7. Handoff to Day 2

Deliverable 1 is verified and its through-line to later work is intact:

- The `to measure` items (now uniformly tagged) are the exact claims **Deliverable 3** must
  replace with numbers — chiefly: does a superseded fact outrank the current one, and how often;
  drift rate under summarisation; proportion of wasted top-k slots.
- Open question 1 (typed extraction may trade F7 for a worse, more authoritative failure) is the
  highest-value thing for **Deliverable 2**'s research scan to find external evidence on, and for
  **Deliverable 3** to settle empirically.
- Capabilities C1–C10 are the fixed vocabulary the research scan (D2) and design (D4) must trace
  every proposed idea back to.
