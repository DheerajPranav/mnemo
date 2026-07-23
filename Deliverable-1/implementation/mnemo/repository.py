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
