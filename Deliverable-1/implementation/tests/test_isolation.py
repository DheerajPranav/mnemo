"""
test_isolation.py — [M1] invariant I1 (tenant isolation), two ways.

1. STATIC: inspect every public method of TenantRepository and assert none accepts a `tenant`
   parameter. This is the mechanical form of the D4 claim "no method can express a cross-tenant
   read" — it fails the build if someone adds a tenant argument later.
2. RUNTIME: load the full multi-tenant D3 dataset into one store; a repo bound to T1 must never
   return a T2 row, and there must be no API to reach another tenant's data.
"""
import inspect
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
IMPL = os.path.abspath(os.path.join(HERE, ".."))
for p in (IMPL, os.path.join(IMPL, "gates")):
    if p not in sys.path:
        sys.path.insert(0, p)

from mnemo.store import connect
from mnemo.repository import TenantRepository
import _dataset


class TestConstructorScopedIsolation(unittest.TestCase):

    def test_no_public_method_accepts_a_tenant_parameter(self):
        """Invariant I1, static form. If this fails, isolation has been weakened structurally."""
        offenders = []
        for name, method in inspect.getmembers(TenantRepository, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            params = inspect.signature(method).parameters
            for pname in params:
                if "tenant" in pname.lower():
                    offenders.append(f"{name}({pname})")
        self.assertEqual(offenders, [], f"methods leak tenant into their signature: {offenders}")

    def test_constructor_requires_a_tenant(self):
        conn = connect()
        with self.assertRaises(ValueError):
            TenantRepository(conn, "")

    def test_repo_never_returns_a_foreign_tenant_row(self):
        conn = connect()
        memories = _dataset.load_memories()
        _dataset.raw_load_into_store(conn, memories)

        t1 = TenantRepository(conn, "T1")
        foreign = [f for f in t1.all_facts() if f.tenant_id != "T1"]
        self.assertEqual(foreign, [], "T1 repo returned foreign-tenant rows")

        # the T2 traps exist in the store, but are invisible to the T1 repo
        t2 = TenantRepository(conn, "T2")
        t2_ids = {f.id for f in t2.all_facts()}
        self.assertIn("m101", t2_ids)                 # trap really is present in the store
        t1_ids = {f.id for f in t1.all_facts()}
        self.assertNotIn("m101", t1_ids)              # but T1 cannot see it
        self.assertNotIn("m102", t1_ids)

    def test_current_facts_are_also_scoped(self):
        conn = connect()
        _dataset.raw_load_into_store(conn, _dataset.load_memories())
        t1 = TenantRepository(conn, "T1")
        self.assertTrue(all(f.tenant_id == "T1" for f in t1.current_facts()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
