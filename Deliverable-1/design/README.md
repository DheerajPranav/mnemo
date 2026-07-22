# design/

Deliverable 4: First-Principles System Design. **Complete** (22 July 2026).

A complete, implementable specification of the improved conversational-memory system. Every component
traces to a capability (C1–C10), premise (P1–P8), or measured failure (F1–F11) from Deliverables 1
and 3; the non-goals in `../reconstruction/problem_reconstruction.pdf` §7.1 are honoured.

## Artifacts (handbook section 6)

| Artifact | What it is |
| :-- | :-- |
| `system_design.pdf` | The full spec — all 11 §6.2 sections, from trust boundaries to milestones + acceptance tests |
| `architecture.pdf` | Component diagram (write/read paths, 2 trust boundaries) + full traceability matrix |
| `data_flow.pdf` | Sequence diagrams (admit / retrieve), the op-selector decision tree, deletion-cascade timing, consolidation |
| `data_model.md` | Postgres schema; every field cites a capability/failure |
| `api_contracts.md` | admit / retrieve / lifecycle / deletion / trace / eval, with the tenant-ambient invariant + acceptance tests |
| `threat_model.md` | Assets, 2 trust boundaries, 6 threats (STRIDE-tagged), mitigations, residual-risk register |
| `decision_records/` | ADR-001…005 (bi-temporal validity · eval scaffold · PII gate · envelope · single-store) |
| `sprint_plan.md` | 5 sprints (S0–S4), risk/dependency-ordered, each ending on an acceptance gate |

Sources for the three PDFs: `../_src/{system_design,architecture,data_flow}.html` → rendered via
`../../_build/topdf.sh`.

## The design in one line
Extract **typed, validity-stamped facts** at admission (PII-gated), store them in a **single
transactional store** with tenant isolation as a **row-level invariant**, resolve conflicts on the
**write path** (not the ranker), and retrieve **tenant-isolated, currently-valid** facts into a
**budgeted, abstaining** injection — every stage traced, the whole thing measured against the D3
baseline.

## Key scope decisions (ADR-004/005)
Designed for the **small/team B2B SaaS** tier (~2×10⁶ facts, single region) — a deliberate downscale
from D1 §4's mid-market assumption — which enables a single Postgres + pgvector store, collapsing the
deletion consistency window (F9) to a transaction. Both decisions are explicitly tier-bound with
recorded scale-up paths.

Feeds Deliverable 5 (Genesis workflow — the sprint gates become BUILD-loop checkpoints) and
Deliverable 6 (implementation + verification — the acceptance tests are the checker's oracle).
