# .genesis/ — Deliverable 5: Genesis Engineering Workflow

**Status: COMPLETE (Day 5, 2026-07-24).** The spine is initialised and seeded from the D4 design, and
three bounded build loops (M1–M3) have shipped through it, each passing a computed gate with independent
L4 verification. Headline: the built system beats the D3 baseline **0/11 → 11/11** on the fixed set.
Per handbook §7.2 the spine was initialised only after the D4 design had a stable first version.

## What this is
Genesis preserves project state and runs implementation as a sequence of **bounded, verifiable loops**.
It is evaluated as an engineering *discipline*, not a code-generation shortcut. The spine was produced by
running the `genesis` kit ritual (G0 cognitive design → G6 prime) — see `genesis.md`.

## Handbook §7.2 required artifacts → where they live
The `genesis` kit uses its own canonical filenames; the mapping to the handbook's required-artifact list:

| Handbook §7.2 requires | This spine provides | Notes |
| :-- | :-- | :-- |
| `.genesis/done.html` | `DONE.html` | locked spec + definition-of-done + milestone plan |
| `.genesis/plan.md` | `PLAN.md` | brainstorm (3 approaches) + M1–M3 sliced with demo commands |
| `.genesis/implementation_notes.html` | `implementation-notes.html` | rolling "what's live now" state |
| `.genesis/context_graph/` | `context-graph.json` | nodes + edges + 6 hand-written invariants (I1–I6) |
| `.genesis/loops/` | `LOOPS.md` | the 5 loops (BUILD/DEBUG/RESEARCH/VERIFY/HEALTH) + 5 gates |
| `.genesis/checkpoints/` | `checkpoints/` | `CURRENT.md` + per-milestone append-only iteration logs |
| `.genesis/wiki/` | `wiki/` | `index.md` pointers into D1–D4; L3 writes distilled pages here |
| `.genesis/decisions/` | `decisions/` | `D5-DR-001` (substrate) + pointers to ADR-001…005 |

Supporting: `genesis.md` (the ritual), `AGENT-ADAPTERS.md` (agent-agnostic verb map),
`KICKOFF.md` (paste-to-resume), `KICKOFF-INTERVIEW.md` + `decisions/0000-template.md` (upstream templates, unmodified).

## §7.3 minimum workflow evidence — where to find each
- **≥3 completed build loops:** M1, M2, M3 — logs in `checkpoints/M1.md`, `M2.md`, `M3.md`.
- **explicit definition of done per milestone:** `DONE.html §2` (global gates) + the per-milestone G0/G1/G2 gate scripts under `../implementation/gates/`.
- **checkpoint before a high-risk change:** `checkpoints/M3-pre-highrisk.md` — taken before the thesis-falsifying read-path change.
- **one documented recovery / rollback / design revision:** the M3 checkpoint log + `implementation-notes.html` deviation table.
- **verification evidence linked from the gate:** each `checkpoints/M*.md` records the L4 VERIFY verdict + the gate-script exit code.
- **current implementation notes + context graph:** `implementation-notes.html`, `context-graph.json`.

## Completion standard (handbook §7.3)
An engineer unfamiliar with the recent work can, from these files alone: read `KICKOFF.md` → `DONE.html`
→ `PLAN.md` → `implementation-notes.html` → `checkpoints/CURRENT.md`, determine the current state,
understand prior decisions, reproduce the gate checks (the demo commands), and resume the next planned
loop — without an oral handover.
