# D6-DR-002 — Postgres + pgvector + RLS ships as a deploy-ready artifact; sqlite stays the runnable substrate

- **Date:** 2026-07-25
- **Status:** accepted
- **Phase / milestone:** Deliverable 6 (Implementation + Independent Verification), applies to M4–M5
- **Relates to:** ADR-005 (single Postgres+pgvector store), D5-DR-001 (stdlib+sqlite loop substrate)

## Context
D5 deferred the production substrate to D6: "re-instate Postgres + pgvector + RLS behind the same
`TenantRepository`." The verification environment still cannot install packages or run services
(PEP-668; no local Postgres), so *running* the Postgres substrate here is impossible. But D6's
completion standard is "the repository can be set up and tested from its documentation" and "all
critical claims are backed by reproducible evidence" — a claim I cannot run is not evidence.

The question is therefore: what is the honest way to honour ADR-005 in D6?

## Decision
Ship the Postgres substrate as a **deploy-ready, reviewable artifact** — `implementation/mnemo/
postgres_schema.sql`, containing the pgvector schema and the **row-level security policies** that put
RLS *behind* the constructor-scoped repository as defence-in-depth — while the **runnable, verified
substrate remains stdlib + sqlite3**. Every acceptance check in handbook §8.3 is executed and evidenced
on the sqlite substrate; the Postgres file is explicitly labelled **not executed here**.

## Consequences
- Positive: no unverifiable claim enters the verification report. Every §8.3 check has a runnable command and a captured result.
- Positive: the isolation guarantee under test is the *load-bearing* one (I1, constructor-scoped repository — a language-level property that holds on any substrate). RLS is defence-in-depth, and shipping it as reviewable SQL means it can be audited even though it is not exercised.
- Positive: `store.py` remains the only module naming a driver (invariant I6), so the migration is a single-file change.
- Negative / cost: RLS is **unverified by execution** in D6. This is carried in the residual-risk register (`verification/security_report.md`) with an explicit owner and the exact command that would verify it on a real Postgres — not silently dropped.
- Negative: pgvector ANN recall behaviour is untested; the ranking evidence is lexical-signal-based (as argued in D3 §2.1 and D5-DR-001).
- **Invariants added to context-graph.json:** none by this decision (I7–I9 come from M4/M5).

## Alternatives rejected
- **Claim the Postgres path works without running it** — would violate the completion standard ("critical claims backed by reproducible evidence") and the project's stated ethos of reporting residuals rather than hiding them.
- **Drop ADR-005 and declare sqlite the production store** — would silently change the D4 architecture (deletion-window and scale arguments in ADR-004/005 depend on the single transactional Postgres store) to make a constraint of the test environment look like a design choice.
