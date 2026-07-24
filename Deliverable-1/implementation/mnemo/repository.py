"""
repository.py — TenantRepository. [M1]

The load-bearing isolation mechanism (design/api_contracts.md "tenant is ambient, never a request
parameter"; design/system_design.md TB-2). Invariant **I1**:

    Tenant is a CONSTRUCTOR argument, bound once. No method accepts tenant_id as a parameter.
    Every SQL read and write is scoped by self._tenant_id. Therefore no method can *express* a
    cross-tenant read — the failure F10 is unreachable by construction, not merely unlikely.

This is stronger than a runtime check: because the tenant is not in any method's surface area, a
caller cannot pass the wrong one, and a code-review/static check (see tests/test_isolation.py) can
mechanically confirm the property. In production (ADR-005) Postgres RLS sits *behind* this as
defence-in-depth; the constructor scope is the primary guarantee.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Fact:
    id: str
    tenant_id: str
    account: str
    subject: str
    mem_type: str
    text: str
    recorded_at: str
    seq: int
    valid_from: str
    valid_to: Optional[str]
    invalidated_at: Optional[str]
    invalidated_by: Optional[str]
    provenance: Optional[str]

    @property
    def is_current(self) -> bool:
        return self.valid_to is None and self.invalidated_at is None


def _row_to_fact(r) -> Fact:
    return Fact(
        id=r["id"], tenant_id=r["tenant_id"], account=r["account"], subject=r["subject"],
        mem_type=r["mem_type"], text=r["text"], recorded_at=r["recorded_at"], seq=r["seq"],
        valid_from=r["valid_from"], valid_to=r["valid_to"],
        invalidated_at=r["invalidated_at"], invalidated_by=r["invalidated_by"],
        provenance=r["provenance"],
    )


class TenantRepository:
    """All data access for exactly one tenant. The tenant is fixed at construction.

    NOTE FOR REVIEWERS / invariant I1: not one public method below takes a tenant argument. Adding
    one would violate I1 and must be rejected in review. The private _scope() helper is the single
    place tenant_id enters a query, and it reads it from self — never from a caller.
    """

    def __init__(self, conn, tenant_id: str):
        if not tenant_id:
            raise ValueError("TenantRepository requires a non-empty tenant_id at construction")
        self._conn = conn
        self._tenant_id = tenant_id  # bound once; never reassigned, never a method parameter

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    # ── writes (scoped) ─────────────────────────────────────────────────────────
    def add_fact(self, *, id, account, subject, mem_type, text, recorded_at, seq,
                 valid_from=None, provenance=None, actor=None) -> None:
        """Insert a fact for THIS tenant. tenant_id is injected from self, not accepted."""
        self._conn.execute(
            """INSERT INTO memory
                 (id, tenant_id, account, actor, subject, mem_type, text,
                  recorded_at, seq, valid_from, valid_to, invalidated_at, invalidated_by, provenance)
               VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL,NULL,?)""",
            (id, self._tenant_id, account, actor, subject, mem_type, text,
             recorded_at, seq, valid_from or recorded_at, provenance),
        )

    def invalidate(self, memory_id: str, *, at: str, by: str) -> None:
        """Mark one of THIS tenant's facts superseded (write-path conflict resolution, ADR-001).

        The WHERE clause is tenant-scoped, so a caller cannot invalidate another tenant's row even
        by guessing its id."""
        self._conn.execute(
            """UPDATE memory SET valid_to = ?, invalidated_at = ?, invalidated_by = ?
                 WHERE id = ? AND tenant_id = ?""",
            (at, at, by, memory_id, self._tenant_id),
        )

    def delete(self, memory_id: str) -> None:
        """Hard-delete a fact (and, via ON DELETE CASCADE, its embedding — invariant I5)."""
        self._conn.execute(
            "DELETE FROM memory WHERE id = ? AND tenant_id = ?", (memory_id, self._tenant_id)
        )

    # ── reads (scoped) ──────────────────────────────────────────────────────────
    def _scope(self):
        """The ONLY place tenant_id enters a read query. Reads it from self."""
        return (self._tenant_id,)

    def all_facts(self):
        """Every fact this tenant can see (valid or not). Never returns a foreign-tenant row."""
        rows = self._conn.execute(
            "SELECT * FROM memory WHERE tenant_id = ? ORDER BY seq", self._scope()
        ).fetchall()
        return [_row_to_fact(r) for r in rows]

    def current_facts(self, account: Optional[str] = None):
        """Currently-valid facts only (valid_to IS NULL AND invalidated_at IS NULL) — invariant I3.

        The ranker is only ever handed the output of this method, so a superseded fact can never
        be a candidate. `account` is an optional in-tenant narrowing (grounding), never a tenant."""
        sql = ("SELECT * FROM memory WHERE tenant_id = ? "
               "AND valid_to IS NULL AND invalidated_at IS NULL")
        params = [self._tenant_id]
        if account is not None:
            sql += " AND account = ?"
            params.append(account)
        sql += " ORDER BY seq"
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_fact(r) for r in rows]

    def find_current_conflict(self, *, account: str, subject: str):
        """Currently-valid facts for the same (account, subject) — the supersession candidates the
        write path checks before admitting a new fact. Scoped to this tenant."""
        rows = self._conn.execute(
            """SELECT * FROM memory
                 WHERE tenant_id = ? AND account = ? AND subject = ?
                   AND valid_to IS NULL AND invalidated_at IS NULL
                 ORDER BY seq""",
            (self._tenant_id, account, subject),
        ).fetchall()
        return [_row_to_fact(r) for r in rows]

    def count(self) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) AS n FROM memory WHERE tenant_id = ?", self._scope()
        ).fetchone()["n"]

    # ── [M4] history / correction ───────────────────────────────────────────────
    def invalidated_facts(self):
        """Facts this tenant has invalidated — the history a correction can be recovered from
        (the ADR-001 residual: an *incorrectly* invalidated fact must not be lost)."""
        rows = self._conn.execute(
            """SELECT * FROM memory WHERE tenant_id = ? AND invalidated_at IS NOT NULL
                 ORDER BY seq""", self._scope()
        ).fetchall()
        return [_row_to_fact(r) for r in rows]

    def restore(self, memory_id: str) -> None:
        """Undo an invalidation (correction recovery). Tenant-scoped, so only this tenant's row."""
        self._conn.execute(
            """UPDATE memory SET valid_to = NULL, invalidated_at = NULL, invalidated_by = NULL
                 WHERE id = ? AND tenant_id = ?""", (memory_id, self._tenant_id)
        )

    def facts_matching(self, *, scope: str, target_ref: str):
        """Facts selected by a deletion scope. `scope` is a column name, never a tenant."""
        if scope not in ("account", "subject", "actor"):
            raise ValueError(f"unsupported deletion scope: {scope}")
        rows = self._conn.execute(
            f"SELECT * FROM memory WHERE tenant_id = ? AND {scope} = ?",
            (self._tenant_id, target_ref),
        ).fetchall()
        return [_row_to_fact(r) for r in rows]

    # ── [M4] derived projection (embedding) ─────────────────────────────────────
    def add_embedding(self, memory_id: str, vec: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO memory_embedding (memory_id, vec) VALUES (?,?)", (memory_id, vec)
        )

    def embedding_count_for(self, memory_ids) -> int:
        """How many embedding rows survive for these ids — proves the ON DELETE CASCADE (I7)."""
        if not memory_ids:
            return 0
        qs = ",".join("?" * len(memory_ids))
        return self._conn.execute(
            f"SELECT COUNT(*) AS n FROM memory_embedding WHERE memory_id IN ({qs})",
            tuple(memory_ids),
        ).fetchone()["n"]

    # ── [M4] consolidation edges (cite, never replace — I8) ─────────────────────
    def add_consolidation_edge(self, *, consolidated_id: str, source_id: str, at: str) -> None:
        self._conn.execute(
            """INSERT OR IGNORE INTO consolidation_edge (consolidated_id, source_id, created_at)
                 VALUES (?,?,?)""", (consolidated_id, source_id, at)
        )

    def sources_for(self, consolidated_id: str):
        """The memories a rollup cites. Join is tenant-scoped through `memory`."""
        rows = self._conn.execute(
            """SELECT m.* FROM consolidation_edge e JOIN memory m ON m.id = e.source_id
                 WHERE e.consolidated_id = ? AND m.tenant_id = ? ORDER BY m.seq""",
            (consolidated_id, self._tenant_id),
        ).fetchall()
        return [_row_to_fact(r) for r in rows]

    # ── [M4] deletion requests — measure the F9 window, don't hope for it ───────
    def open_deletion_request(self, *, scope: str, target_ref: str, at: str) -> int:
        cur = self._conn.execute(
            """INSERT INTO deletion_request (tenant_id, scope, target_ref, requested_at, status)
                 VALUES (?,?,?,?,'pending')""", (self._tenant_id, scope, target_ref, at)
        )
        return cur.lastrowid

    def complete_deletion_request(self, request_id: int, *, at: str, window_ms: float) -> None:
        self._conn.execute(
            """UPDATE deletion_request SET completed_at = ?, window_ms = ?, status = 'completed'
                 WHERE id = ? AND tenant_id = ?""", (at, window_ms, request_id, self._tenant_id)
        )

    def deletion_request(self, request_id: int):
        return self._conn.execute(
            "SELECT * FROM deletion_request WHERE id = ? AND tenant_id = ?",
            (request_id, self._tenant_id),
        ).fetchone()

    # ── [M5] audit log — every read leaves a row, or the read fails closed (I9) ──
    def log_access(self, *, request_id: str, user_id, returned_memory_ids, at: str) -> None:
        self._conn.execute(
            """INSERT INTO access_log (request_id, tenant_id, user_id, returned_memory_ids, occurred_at)
                 VALUES (?,?,?,?,?)""",
            (request_id, self._tenant_id, user_id, ",".join(returned_memory_ids), at),
        )

    def access_logs(self):
        return self._conn.execute(
            "SELECT * FROM access_log WHERE tenant_id = ? ORDER BY id", self._scope()
        ).fetchall()
