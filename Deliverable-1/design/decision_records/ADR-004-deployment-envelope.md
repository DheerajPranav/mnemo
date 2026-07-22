# ADR-004: Deployment envelope — small/team B2B SaaS tier for v1

**Status:** accepted (v1 scope)
**Date:** 2026-07-22
**Deliverable:** D4 (System Design). Overrides the unmeasured scale assumption in D1 §4.
**Traces to:** premises P2, P5, P6; constraint envelope in `../../reconstruction/first_principles.md` §4.

## Context
D1 §4 set a constraint envelope against a **mid-market** target — *"50 tenants × 200 users × 10,000
memories = 10⁸ memories"* — explicitly flagged `[ASSUMPTION]` and "revisable with a recorded reason."
For the v1 design we are deliberately choosing the **smaller** end of the deployment spectrum, because
the point of v1 is a system another engineer can implement and that we can measure end-to-end, not one
provisioned for peak scale. This ADR records the chosen numbers so every downstream decision (storage,
isolation, deletion window, index type) designs against something concrete.

## Decision
Design v1 for a **small / team B2B SaaS** deployment:

| Dimension | v1 target (small/team) | D1 §4 (mid-market, superseded for v1) |
| :-- | :-- | :-- |
| Tenants | ≤ 50 | 50 |
| Users / tenant | ≤ 20 | 200 |
| Memories / account | ≤ 2,000 | 10,000 |
| **Total typed facts (corpus)** | **≤ ~2 × 10⁶** | ~10⁸ |
| Region | single region | (unspecified) |
| Memory injection budget | ≤ 2,000 tokens of 16,000 | unchanged |
| Memory subsystem latency | **p95 ≤ 300 ms** (retrieve+rank+construct); end-to-end read ≤ 500 ms | p95 ≤ 300 ms |
| Memory subsystem cost | ≤ 15 % of per-turn token spend | unchanged |
| Deletion consistency | **near-synchronous typical (≤ ~5 s), ≤ 24 h guaranteed & tested** | ≤ 60 s / ≤ 24 h |
| Cross-tenant leakage | **zero, tested adversarially** | zero |
| Retrieval quality | beat the D3 naive baseline on the fixed set | unchanged |

## Consequences and trade-offs
- (+) ~2 × 10⁶ facts fit comfortably in a single Postgres instance with a pgvector HNSW index → enables
  the single-store architecture in **ADR-005**, which in turn makes deletion near-synchronous (the
  biggest correctness win at this tier).
- (+) Single region removes data-residency routing from v1's critical path (the Initech EU-residency
  case is handled as an *account attribute / requirement* fact, not yet as infra-level regional
  partitioning — see non-goal).
- (−) The design is **not** provisioned for mid-market at these settings; the scale-up path (dedicated
  vector store, regional partitioning, async everything) is recorded in ADR-005 "Revisit conditions"
  and is explicitly out of v1 scope.
- (−) Latency/cost headroom is generous at this scale, so v1 may under-exercise the C6 budgeting and
  C5 ranking-cost tensions; D6 load tests must therefore *synthetically* push corpus size to confirm
  the p95 targets hold as the index grows, not just at day-one volume.

## Revisit conditions
- **Revisit** the whole envelope (and ADR-005) when any single tenant approaches ~10⁵ memories or the
  deployment adds a second region; at that point the single-store assumption breaks and the dual-store
  deletion window from D1 §4 returns as a real design problem.
- **Tighten** the deletion "typical" figure once D6 measures it under load; ≤ 5 s is a design target,
  not yet a measured guarantee.
