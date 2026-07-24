"""
store.py — the physical store. sqlite3 dialect of design/data_model.md.

[M1] Isolation invariant I6 (domain purity): this is the ONLY module that names a concrete DB
driver. Everything above it (repository, admission, ranking) talks to a repository, never to
sqlite directly. Swapping to Postgres + pgvector (ADR-005) in Deliverable 6 changes only this file.

Schema (lean but faithful to data_model.md):
  memory            — typed facts + bi-temporal validity + provenance
  memory_embedding  — derived projection; ON DELETE CASCADE demonstrates invariant I5
                      (a delete removes the fact and its projection in one transaction; the
                       deletion consistency window F9 collapses to a txn — ADR-005).
"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    id            TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL,               -- tenant partition (invariant I1)
    account       TEXT NOT NULL,               -- the account the fact is about
    actor         TEXT,                        -- who recorded it (provenance)
    subject       TEXT NOT NULL,               -- typed slot, e.g. crm / dm / budget (extraction)
    mem_type      TEXT NOT NULL,               -- fact | preference | event  (extraction)
    text          TEXT NOT NULL,
    recorded_at   TEXT NOT NULL,               -- wall-clock the fact was captured (ts)
    seq           INTEGER NOT NULL,            -- monotonic ingestion order; supersession tiebreak
    valid_from    TEXT NOT NULL,               -- bi-temporal (ADR-001)
    valid_to      TEXT,                        -- NULL => currently valid
    invalidated_at TEXT,                       -- set on the WRITE path when superseded
    invalidated_by TEXT,                       -- id of the fact that superseded this one
    provenance    TEXT                         -- free-form source pointer
);
CREATE INDEX IF NOT EXISTS ix_memory_scope ON memory (tenant_id, account, subject);
CREATE INDEX IF NOT EXISTS ix_memory_valid ON memory (tenant_id, valid_to);

CREATE TABLE IF NOT EXISTS memory_embedding (
    memory_id TEXT PRIMARY KEY,
    vec       TEXT NOT NULL,                   -- serialized sparse tf-idf (placeholder for pgvector)
    FOREIGN KEY (memory_id) REFERENCES memory(id) ON DELETE CASCADE
);

-- [M4] consolidation_edge — a rollup memory CITES its sources; it never replaces them (C7, F5/F6).
CREATE TABLE IF NOT EXISTS consolidation_edge (
    consolidated_id TEXT NOT NULL,             -- the summary/rollup memory
    source_id       TEXT NOT NULL,             -- a memory it cites
    created_at      TEXT NOT NULL,
    PRIMARY KEY (consolidated_id, source_id),
    FOREIGN KEY (consolidated_id) REFERENCES memory(id) ON DELETE CASCADE,
    FOREIGN KEY (source_id)       REFERENCES memory(id) ON DELETE CASCADE
);

-- [M5] access_log — one row per retrieval; reconstruct who saw what, prove no cross-tenant read (C8/C9).
CREATE TABLE IF NOT EXISTS access_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id          TEXT NOT NULL,         -- joins to the decision trace
    tenant_id           TEXT NOT NULL,
    user_id             TEXT,
    returned_memory_ids TEXT NOT NULL,         -- exactly what was injected (comma-joined)
    occurred_at         TEXT NOT NULL
);

-- [M4] deletion_request — erasure job; completed_at - requested_at IS the measured F9 window (C7).
CREATE TABLE IF NOT EXISTS deletion_request (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id    TEXT NOT NULL,
    scope        TEXT NOT NULL,                -- subject | account | user | tenant
    target_ref   TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    completed_at TEXT,
    window_ms    REAL,                         -- completed - requested, in ms (proves the window)
    status       TEXT NOT NULL DEFAULT 'pending'  -- pending | completed | failed
);
"""


def connect(path=":memory:"):
    """Open a connection with the schema applied and FK cascade enforced.

    `PRAGMA foreign_keys = ON` is what makes ON DELETE CASCADE (invariant I5) actually fire in
    sqlite — it is off by default. Row factory is sqlite3.Row so callers read columns by name.
    """
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
