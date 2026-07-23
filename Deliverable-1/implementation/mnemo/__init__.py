"""
Mnemo — conversational-memory intelligence system (reference implementation).

Built across the Deliverable-5 Genesis build loops (M1–M3) as bounded, verifiable changes,
each seeded from the Deliverable-4 design and gated against the *same* fixed dataset the
Deliverable-3 baseline was measured on. Substrate is pure-stdlib + sqlite3 for the loops
(decision D5-DR-001); production substrate is Postgres + pgvector + RLS (ADR-005), re-instated
in Deliverable 6.

Module map (context-graph.json nodes):
  store       — sqlite connection + schema (data_model.md, sqlite dialect)     [M1]
  repository  — TenantRepository: tenant is a constructor arg, never a param    [M1]  invariant I1
  pii_gate    — deterministic (Presidio-style) PII recognizer                    [M2]  invariant I2
  extraction  — raw record -> typed, validity-stamped Fact                       [M2]
  admission   — write path: pii-gate -> persist -> invalidate superseded         [M2]  invariant I3
  retrieval   — tenant-scoped, validity-filtered candidate fetch                 [M3]
  ranking     — hand-specified multi-signal ranker over currently-valid facts    [M3]  invariant I3
  injection   — budgeted, de-duplicated, abstaining context selection            [M3]  invariant I4
"""
