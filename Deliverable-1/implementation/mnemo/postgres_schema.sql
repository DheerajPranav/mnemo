-- postgres_schema.sql — the PRODUCTION substrate (ADR-005): Postgres + pgvector + row-level security.
--
-- STATUS: **NOT EXECUTED in this repository's verification run.** The verification environment cannot
-- run a Postgres service (see decision .genesis/decisions/D6-DR-002). Every acceptance check in
-- handbook §8.3 is executed and evidenced on the sqlite substrate (mnemo/store.py); this file is the
-- reviewable, deploy-ready form of the same schema, and its RLS status is carried as an OPEN residual
-- in verification/security_report.md — not claimed as verified.
--
-- Design intent: RLS sits BEHIND the constructor-scoped TenantRepository (invariant I1) as
-- defence-in-depth. The repository is the primary guarantee (a language-level property that holds on
-- any substrate); RLS is the second wall for raw-SQL/ops access paths that bypass the application.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE memory_type   AS ENUM ('fact', 'preference', 'event');
CREATE TYPE deletion_scope AS ENUM ('subject', 'account', 'user', 'tenant');
CREATE TYPE deletion_status AS ENUM ('pending', 'completed', 'failed');

-- ── core: typed facts + bi-temporal validity + provenance ────────────────────────────────────
CREATE TABLE memory (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      uuid        NOT NULL,
    account        text        NOT NULL,
    actor          uuid,
    subject        text        NOT NULL,
    mem_type       memory_type NOT NULL,
    text           text        NOT NULL,
    recorded_at    timestamptz NOT NULL,
    seq            bigint      NOT NULL,          -- monotonic ingestion order; supersession tiebreak
    valid_from     timestamptz NOT NULL,
    valid_to       timestamptz,                   -- NULL => currently valid
    invalidated_at timestamptz,
    invalidated_by uuid REFERENCES memory(id),    -- self-relation: supersession (ADR-001)
    provenance     text
);
CREATE INDEX ix_memory_scope ON memory (tenant_id, account, subject);
CREATE INDEX ix_memory_valid ON memory (tenant_id, valid_to);

-- Derived projection. Rebuildable from `memory`; cascades so deletion is one transaction (I5/I7).
CREATE TABLE memory_embedding (
    memory_id uuid PRIMARY KEY REFERENCES memory(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL
);
CREATE INDEX ix_memory_embedding_ann ON memory_embedding
    USING hnsw (embedding vector_cosine_ops);

-- ── lifecycle + audit ────────────────────────────────────────────────────────────────────────
CREATE TABLE consolidation_edge (            -- a rollup CITES its sources; never replaces them (I8)
    consolidated_id uuid NOT NULL REFERENCES memory(id) ON DELETE CASCADE,
    source_id       uuid NOT NULL REFERENCES memory(id) ON DELETE CASCADE,
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (consolidated_id, source_id)
);

CREATE TABLE access_log (                    -- one row per retrieval; audit fails closed (I9)
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id          uuid        NOT NULL,
    tenant_id           uuid        NOT NULL,
    user_id             uuid,
    returned_memory_ids uuid[]      NOT NULL,
    occurred_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE deletion_request (              -- completed_at - requested_at IS the measured F9 window
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    uuid            NOT NULL,
    scope        deletion_scope  NOT NULL,
    target_ref   text            NOT NULL,
    requested_at timestamptz     NOT NULL DEFAULT now(),
    completed_at timestamptz,
    status       deletion_status NOT NULL DEFAULT 'pending'
);

-- ── row-level security: defence-in-depth behind the repository (TB-2) ────────────────────────
-- The application sets `SET LOCAL app.tenant_id = '<uuid>'` once per transaction, from the same
-- constructor-bound tenant the repository holds. No statement can read across tenants even if a
-- WHERE clause is omitted by mistake or a raw psql session is used with a non-superuser role.
ALTER TABLE memory             ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_log         ENABLE ROW LEVEL SECURITY;
ALTER TABLE deletion_request   ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory             FORCE ROW LEVEL SECURITY;
ALTER TABLE access_log         FORCE ROW LEVEL SECURITY;
ALTER TABLE deletion_request   FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_memory ON memory
    USING      (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation_access_log ON access_log
    USING      (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation_deletion_request ON deletion_request
    USING      (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Verification command that WOULD close the residual on a real Postgres (see security_report.md R-P1):
--   SET LOCAL app.tenant_id = '<tenant-A-uuid>';
--   SELECT count(*) FROM memory WHERE tenant_id = '<tenant-B-uuid>';   -- must return 0
