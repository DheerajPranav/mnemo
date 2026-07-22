# Baseline Protocol — Naive Conversational-Memory Retrieval

**Project:** Conversational Memory Intelligence System (GTM / B2B SaaS)
**Author:** Dheeraj Pranav
**Date:** 22 July 2026
**Deliverable:** 3 of 8 — Productive Failure Baseline, *Learning Through Reconstruction* handbook v1.0
**Status:** run complete — see `baseline_results.csv`, `error_examples.jsonl`, `productive_failure_report.pdf`

This protocol is the pre-registration of the experiment: what the baseline is, what workload it
runs against, how each metric is defined, and how to reproduce every number. The measured results
and their interpretation live in `productive_failure_report.pdf`; this document is what makes those
numbers auditable.

---

## 1. Hypothesis

> The strongest of the *simpler* memory designs — single-signal retrieval over stored transcript
> chunks (Approach D in `../reconstruction/failure_analysis.md`) — fails on the GTM workload not
> because its retriever is weak, but because whole classes of requirement live **outside** what a
> similarity signal can express: temporal validity, resolved meaning, admission control, and tenant
> isolation. These failures are therefore **structural, not signal-tunable**: a better embedder
> re-orders the same wrong candidate set; it does not add a validity field, a tenant boundary, or a
> PII gate.

The baseline is built to *falsify* this if it can — if naive retrieval handles the adversarial
conditions, the whole system design in Deliverable 1 is over-engineered and must be cut back.

## 2. The baseline system (`naive_baseline/`)

Approach D, implemented literally: **store every chunk, retrieve top-*k* by one similarity signal,
inject in similarity order until a token budget is hit.** Nothing else.

Deliberately absent — and their absence is the point of the measurement:

| Missing mechanism | What its absence should cause |
| :-- | :-- |
| Admission control (extraction, salience, PII gate) | F8 index saturation, F11 sensitive data retained |
| Typed / resolved facts (vs raw utterance chunks) | F7 chunk inverts out of context |
| Temporal validity + supersession | F4 superseded fact served as current |
| Multi-signal ranking (recency, importance, validity) | F4, and no way to prefer current over stale |
| Index-level tenant partitioning | F10 cross-tenant leakage |
| Abstention threshold | cold-start: injects noise instead of saying "nothing on file" |
| Consolidation / decay / deletion | out of scope for a retrieval-only baseline — see §7 |

### 2.1 Similarity signal: lexical TF-IDF cosine (and why)

The signal is cosine similarity over smoothed TF-IDF vectors, pure Python standard library — no
numpy, no embedding-model download, no API key. `idf(t) = ln((1+N)/(1+df_t)) + 1`, term-frequency
normalised by document length, deterministic `(-score, id)` tie-break.

**Why lexical, not a dense embedder** — a deliberate, documented trade:

- **Reproducibility first.** The environment blocks `pip install` (PEP 668, externally-managed).
  A stdlib baseline runs on any Python 3.8+ with a fixed seed and produces byte-identical results
  on any machine, which is worth more for a *baseline* than a marginal retrieval-quality gain.
- **The hypothesis is about what similarity *cannot express*, not about how good the embedder is.**
  Every failure this baseline targets (validity, isolation, admission, resolved meaning) is
  *orthogonal* to the choice of similarity function. A dense embedder would move scores around
  inside the same wrong candidate set; it would not add a tenant boundary or a valid-to field.
- **Threat to validity, stated honestly (§8).** A lexical signal *over-rewards surface overlap*.
  The dataset is authored so this bias runs **in the baseline's favour** where it matters — stale
  facts are phrased with *more* query-term overlap than their corrections — so a lexical retriever
  is a *harder* baseline to beat on supersession, not an easier one. Where a dense model would
  plausibly differ (e.g. paraphrased corrections) is flagged per-case in the report.

The report's claims are limited to what a *single-signal* retriever does; they are not claims about
TF-IDF specifically.

## 3. Workload (`naive_baseline/data/`)

A fixed, seeded, hand-authored GTM dataset. `build_dataset.py` regenerates it deterministically
(`SEED = 20260722`); both JSONL files are committed so results are fixed even without re-running.

- **44 memories.** 1 PII (`m009`), 3 foreign-tenant (`m101–m103`), 30 filler/duplicate
  (`duplicate_or_filler_ratio = 0.682`), the remainder substantive current/superseded facts.
- **Two tenants.** T1 *Northwind* (the querying customer) and T2 *Contoso* — **both have an account
  named "Acme"** with lexically near-identical notes. This is the cross-tenant trap (F10).
- **Adversarial by construction.** Stale facts are phrased with more surface overlap with a natural
  query than their corrections; a single similarity signal is *forced* to prefer the stale one. The
  traps are hand-authored, not accidental.

### 3.1 The six required workload conditions (handbook §5.2)

Every condition is covered by ≥1 query, each naming a `gold` (correct current memory or `ABSTAIN`)
and a `trap` (the memory that must **not** win):

| # | Condition (handbook) | Queries | Probes |
| :-- | :-- | :-- | :-- |
| 1 | Irrelevant + contradictory memories retrievable | q01, q02, q03, q11 | F4, F8 |
| 2 | Preferences that change over time (supersession) | q01, q02, q03 | F4 |
| 3 | Long conversation, constrained token budget (buried fact) | q08 | F3, F8 |
| 4 | Multiple users/tenants with similar wording | q05, q06 | F4, F10 |
| 5 | Sensitive info that should not be retained/surfaced | q07 (+ leaks into q04, q09) | F11 |
| 6 | Cold start / no relevant memory → should abstain | q09, q10 | cold-start |

An additional out-of-context inversion case (q04, probe F7) exercises "a chunk is not a resolved
fact." Eleven queries total.

## 4. Fixed parameters

| Parameter | Value | Rationale |
| :-- | :-- | :-- |
| `K` (top-k retrieved) | 5 | small enough that wasted slots hurt recall; typical injection breadth |
| `TOKEN_BUDGET` | 2000 | the Deliverable 1 constraint (≤2000 of a 16000 window reserved for memory) |
| `ABSTAIN_THRESHOLD` | 0.10 | a *reference* threshold only; **the naive baseline does not apply it** (it never abstains) |
| `LATENCY_REPEATS` | 200 | repeats per query for a stable per-retrieval latency sample |
| token estimate | `round(words × 1.3)` | cheap deterministic proxy for budgeting; documented approximation |

## 5. Metrics (exact definitions)

Written to `baseline_results.csv` (per-query rows + an aggregate block) and `metrics.json`.

| Metric | Definition |
| :-- | :-- |
| `overall_accuracy` | fraction of queries that pass **every** condition-appropriate check (no trap above gold, no leak, no PII, correct abstention) |
| `recall_at_k` | of *answerable* queries (gold ≠ ABSTAIN), fraction with gold in top-*k* |
| `supersession_failure_rate` | of F4-probed queries, fraction where the superseded `trap` outranks the current `gold` |
| `inversion_failures` | count of F7 queries where the inverting utterance outranks the resolved fact |
| `cross_tenant_leak_rate` | of F10-probed queries, fraction with a foreign-tenant memory in top-*k* |
| `pii_exposure_count` | number of queries that **inject** a PII-flagged memory into context |
| `coldstart_abstention_failure_rate` | of cold-start queries, fraction that inject anything instead of abstaining |
| `wasted_topk_slot_rate` | of answerable queries' top-*k* slots, fraction occupied by filler/duplicate memories |
| `duplicate_or_filler_ratio` | fraction of the *corpus* that is filler/duplicate (index-health measure) |
| `avg` / `max_injected_tokens` | injected-context size under the budget |
| `latency_p50/p95_ms` | per-retrieval latency over `n_queries × LATENCY_REPEATS` samples |

Pass/fail is **condition-appropriate**, not a single global rule: a cold-start query passes by
abstaining; an answerable query passes by putting gold above any trap with no leak and no PII.

## 6. How to reproduce

```bash
cd experiments/naive_baseline
python3 build_dataset.py     # writes data/memories.jsonl, data/queries.jsonl  (SEED=20260722)
python3 evaluate.py          # writes ../baseline_results.csv, ../error_examples.jsonl, metrics.json
```

Pure standard library; no install step, no network, no API key. Deterministic **for every failure /
correctness metric** — re-running yields byte-identical results; only `latency_p50_ms` /
`latency_p95_ms` vary (wall-clock, 3rd-decimal jitter). `evaluate.py` prints the aggregate to stdout.

## 7. Deliberately out of scope for this baseline

A retrieval-only baseline structurally cannot exercise the failures that require a *different*
mechanism. Naming them keeps the report honest:

- **F1** (correction doesn't survive a session) and **F2** (quadratic prompt growth) need a
  multi-turn session with a write path — this harness is single-shot retrieval.
- **F5 / F6** (summarisation loss / drift) need a summariser — the baseline stores raw chunks and
  never compresses.
- **F9** (deleted memory still retrievable) needs a delete-then-requery test against a dual store.

These move to the Deliverable 6 verification harness. This baseline measures the five failures a
naive retriever *does* produce (F4, F7, F8, F10, F11) plus the cold-start abstention failure — which
is exactly where Deliverable 1 §6 concentrates the design pressure.

## 8. Threats to validity

1. **Signal specificity.** Lexical TF-IDF over-rewards surface overlap. Mitigated by authoring the
   adversarial cases so the bias favours the *stale* fact (a harder supersession test) and by
   restricting claims to "single-signal retrieval," not "TF-IDF." A dense-embedder arm is future
   work (Deliverable 4's 3-arm comparison: naive / +recency / validity-filter).
2. **Hand-authored dataset.** Small (44 memories, 11 queries) and constructed by the author, so it
   demonstrates *existence* and *character* of each failure, not population frequencies. It is a
   diagnostic set, not a benchmark; the LongMemEval-scaffolded set (ADR-002) is the larger follow-on.
3. **Token-budget non-binding.** Injected context stayed far under 2000 tokens (chunks are short),
   so the budget never bound in this run. That is itself a finding: at k=5 the failure is *what*
   gets selected, not *how much* — budget pressure is a Deliverable 6 concern with longer memories.
4. **Cold-start via similarity gap only.** The baseline's non-abstention is measured against a
   reference 0.10 threshold it does not apply; the "correct" abstention behaviour is defined by the
   dataset (no gold exists), not by a tuned threshold.
```
