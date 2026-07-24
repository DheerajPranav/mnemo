"""test_lifecycle.py — [M4] correction, deletion, expiry, consolidation.

Includes the regression lock for the D6/M4 finding: supersession must apply ONLY to slot-valued
types (fact/preference). Event memories accumulate; superseding them silently destroyed 31 of 40
memories and made the M3 read-path gate pass for the wrong reason.
"""
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
from mnemo import admission, retrieval, ranking, injection, lifecycle, consolidation
import _dataset


def _pipeline():
    conn = connect()
    repos = {}
    admission.admit_all(repos, _dataset.load_memories(), lambda t: TenantRepository(conn, t))
    conn.commit()
    return conn, repos["T1"]


def _answer_ids(repo, query, account):
    ranked = ranking.rank(query, account, retrieval.candidates(repo, account))
    return [r.fact.id for r in injection.select(ranked, account)]


class TestSupersessionScope(unittest.TestCase):
    """The D6/M4 regression: only fact/preference supersede."""

    def setUp(self):
        self.conn, self.repo = _pipeline()
        self.addCleanup(self.conn.close)

    def test_event_memories_accumulate_and_are_not_superseded(self):
        threads = [f for f in self.repo.current_facts(account="Initech") if f.subject == "thread"]
        self.assertGreater(len(threads), 1,
                           "thread turns were superseded — event memories must accumulate (F5)")
        self.assertTrue(all(f.mem_type == "event" for f in threads))

    def test_slot_valued_facts_still_supersede(self):
        crm = [f for f in self.repo.current_facts(account="Acme") if f.subject == "crm"]
        self.assertEqual(len(crm), 1, "a slot-valued fact must hold exactly one current value")
        self.assertEqual(crm[0].id, "m002")

    def test_only_genuine_conflicts_are_invalidated(self):
        invalid = {f.id for f in self.repo.invalidated_facts()}
        for trap in ("m001", "m003", "m005", "m007"):
            self.assertIn(trap, invalid)


class TestDeletion(unittest.TestCase):
    def setUp(self):
        self.conn, self.repo = _pipeline()
        self.addCleanup(self.conn.close)

    def test_delete_removes_from_storage_and_retrieval_and_cascades(self):
        q = "What is Acme's approved budget for the deal?"
        self.assertIn("m008", _answer_ids(self.repo, q, "Acme"))

        res = lifecycle.delete(self.repo, scope="subject", target_ref="budget")
        self.conn.commit()

        self.assertIn("m008", res.deleted_ids)
        self.assertEqual(res.embeddings_remaining, 0, "derived projection outlived its source (I7)")
        self.assertEqual([f.id for f in self.repo.all_facts() if f.id in res.deleted_ids], [])
        self.assertNotIn("m008", _answer_ids(self.repo, q, "Acme"))

    def test_deletion_window_is_recorded(self):
        res = lifecycle.delete(self.repo, scope="account", target_ref="Initech")
        self.conn.commit()
        row = self.repo.deletion_request(res.request_id)
        self.assertEqual(row["status"], "completed")
        self.assertIsNotNone(row["completed_at"])
        self.assertIsNotNone(row["window_ms"])

    def test_delete_cannot_touch_another_tenant(self):
        t2 = TenantRepository(self.conn, "T2")
        before = t2.count()
        lifecycle.delete(self.repo, scope="account", target_ref="Acme")   # T1 repo
        self.conn.commit()
        self.assertEqual(t2.count(), before, "a T1 deletion removed T2 rows")


class TestCorrectionRecovery(unittest.TestCase):
    def test_incorrectly_invalidated_fact_is_recoverable(self):
        conn, repo = _pipeline()
        self.addCleanup(conn.close)
        repo.invalidate("m020", at="2026-07-25", by="operator-error")
        conn.commit()
        self.assertNotIn("m020", {f.id for f in repo.current_facts()})
        self.assertIn("m020", {f.id for f in repo.invalidated_facts()})   # kept in history
        self.assertTrue(lifecycle.restore(repo, "m020"))
        self.assertIn("m020", {f.id for f in repo.current_facts()})


class TestConsolidation(unittest.TestCase):
    def test_rollup_cites_and_never_replaces_its_sources(self):
        conn, repo = _pipeline()
        self.addCleanup(conn.close)
        before = {f.id for f in repo.current_facts()}
        rollup_id, sources = consolidation.consolidate(
            repo, account="Initech", subject="thread", rollup_id="r001",
            summary_text="Rollup of the Initech thread.", at="2026-07-25", seq=9000)
        conn.commit()

        self.assertGreater(len(sources), 1)
        after = {f.id for f in repo.current_facts()}
        self.assertTrue(before.issubset(after), "consolidation invalidated a source (F5)")
        self.assertEqual(sorted(f.id for f in consolidation.rederive(repo, rollup_id)),
                         sorted(sources), "rollup is not re-derivable from its sources")

    def test_rollup_uses_a_distinct_subject_so_it_cannot_supersede_sources(self):
        self.assertTrue(consolidation.rollup_subject("thread").endswith("#rollup"))


class TestExpiry(unittest.TestCase):
    def test_expires_old_events_but_not_facts(self):
        conn, repo = _pipeline()
        self.addCleanup(conn.close)
        facts_before = {f.id for f in repo.current_facts() if f.mem_type in ("fact", "preference")}
        expired = lifecycle.expire_events(repo, now_date="2026-07-25", ttl_days=180)
        conn.commit()
        current = {f.id for f in repo.current_facts()}
        self.assertTrue(expired, "expiry swept nothing")
        self.assertTrue(facts_before.issubset(current), "expiry removed a slot-valued fact")
        for eid in expired:
            self.assertNotIn(eid, current)


if __name__ == "__main__":
    unittest.main(verbosity=2)
