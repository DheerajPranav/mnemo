"""test_trace.py — [M5] decision traces (C9) and the fail-closed audit (I9 / threat R5)."""
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
from mnemo import admission, trace
import _dataset


def _pipeline():
    conn = connect()
    repos = {}
    admission.admit_all(repos, _dataset.load_memories(), lambda t: TenantRepository(conn, t))
    conn.commit()
    return conn, repos["T1"]


class TestTrace(unittest.TestCase):
    def setUp(self):
        self.conn, self.repo = _pipeline()
        self.addCleanup(self.conn.close)
        trace.clear()

    def test_trace_records_the_injected_set_and_is_retrievable_by_request_id(self):
        injected, t = trace.traced_retrieve(
            self.repo, query="What CRM platform does Acme use?", account="Acme",
            request_id="r1", user_id="u_ann")
        self.assertIn("m002", t.injected_ids)
        self.assertEqual(t.explain("m002"), "injected")
        self.assertIs(trace.get_trace("r1"), t)

    def test_trace_localises_a_memory_dropped_before_the_ranker(self):
        self.repo.invalidate("m002", at="2026-07-25", by="test")
        self.conn.commit()
        _, t = trace.traced_retrieve(self.repo, query="What CRM platform does Acme use?",
                                     account="Acme", request_id="r2")
        self.assertNotIn("m002", t.candidate_ids)
        self.assertEqual(t.explain("m002"), "not_a_candidate")

    def test_trace_records_abstention_with_a_reason(self):
        _, t = trace.traced_retrieve(
            self.repo, query="What is Acme's preferred data center region for hosting?",
            account="Acme", request_id="r3")
        self.assertTrue(t.abstained)
        self.assertEqual(t.injected_ids, [])
        self.assertTrue(any("abstain" in n for n in t.notes))

    def test_every_retrieval_writes_exactly_one_audit_row(self):
        for i, q in enumerate(["What CRM platform does Acme use?",
                               "Who is the decision maker at Acme?"]):
            trace.traced_retrieve(self.repo, query=q, account="Acme", request_id=f"a{i}")
        self.conn.commit()
        rows = self.repo.access_logs()
        self.assertEqual(len({r["request_id"] for r in rows}), 2)
        self.assertTrue(all(r["tenant_id"] == "T1" for r in rows))

    def test_read_fails_closed_when_the_audit_write_fails(self):
        class BrokenAudit:
            def __init__(self, inner):
                self._inner = inner

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def log_access(self, **kwargs):
                raise RuntimeError("audit backend unavailable")

        with self.assertRaises(trace.AuditWriteError):
            trace.traced_retrieve(BrokenAudit(self.repo), query="What CRM platform does Acme use?",
                                  account="Acme", request_id="broken")


if __name__ == "__main__":
    unittest.main(verbosity=2)
