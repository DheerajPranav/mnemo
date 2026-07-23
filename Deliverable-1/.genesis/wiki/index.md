# Wiki Index — Mnemo

The project knowledge base. Same schema as the agentic-swe-kit wiki: concept pages in `concepts/`,
each with frontmatter and ≥2 `[[wikilinks]]`. The L3 RESEARCH loop writes here; G0 reads here first.

> **Read this file before any milestone (G0 step 1).** Pick candidate pages by name-matching the
> milestone's nouns, then drill in. The wiki is what prevents rebuilding work that already exists.

> Mnemo's deep knowledge already lives in the D1–D4 artifacts. Rather than copy it, this index
> **points** at the authoritative source for each noun a loop will touch. Treat these as the wiki's
> concept pages until a loop needs to distil one into `concepts/`.

## Entities (the things this system has)
- **Memory (typed fact)** — schema + bi-temporal validity fields → `../../design/data_model.md` (`memory` table)
- **TenantRepository** — constructor-scoped data access; tenant is never a method parameter → `../../design/api_contracts.md` (tenant-ambient invariant) + invariant **I1**
- **Admission (write path)** — extract → PII-gate → persist → invalidate-superseded → `../../design/data_flow.md` (admit sequence)
- **Retrieval + ranker** — validity-filtered, multi-signal, budgeted, abstaining → `../../design/data_flow.md` (retrieve sequence)
- **Baseline (numbers to beat)** — measured naive retriever → `../../experiments/baseline_results.csv`

## Concepts (how it works)
- **Fixed vocabulary C1–C10 / F1–F11 / P1–P8** — everything traces to these → `../../reconstruction/first_principles.md`, `../../reconstruction/failure_analysis.md`
- **Bi-temporal validity (conflict resolution on the write path)** → `../../design/decision_records/ADR-001/` · invariant **I3**
- **PII admission gate (deterministic-first, Presidio-style)** → `../../design/decision_records/ADR-003/` · invariant **I2**
- **Single-store / deletion-cascade** → `../../design/decision_records/ADR-005-postgres-pgvector-single-store.md` · invariant **I5**
- **Threat model (TB-1 admission, TB-2 isolation, R4 memory-borne prompt injection)** → `../../design/threat_model.md`
- **Sprint plan → gate mapping (S0→G0, S1→G1, S2→G2)** → `../../design/sprint_plan.md`

## Sources (research distilled by L3)
<!-- L3 RESEARCH writes distilled source pages here. -->
- _(none yet — the first L3 pass, e.g. Presidio recognizer set for M2, will file one here)_

## Seeded from agentic-swe-kit
Relevant global concept pages for this project's phases (pointers only — read on demand):
- `$AGENTIC_SWE_WIKI_ROOT/clean-architecture/` — when deciding module boundaries (M1: repository behind `store`; invariant **I6** domain purity)
- `$AGENTIC_SWE_WIKI_ROOT/security-engineering/` — untrusted-input handling (M2 PII gate; R4 prompt-injection frontier)
- `$AGENTIC_SWE_WIKI_ROOT/data-systems/` — transactional store + derived projections (M1/M3)
- `$AGENTIC_SWE_WIKI_ROOT/testing/` — evaluation-as-a-gate; the D3 fixed set is the oracle (M3)
