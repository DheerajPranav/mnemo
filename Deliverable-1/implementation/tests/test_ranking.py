"""test_ranking.py — [M3] the read path: validity filter, abstain, account-grounding, tie resolution.

These lock in the M3 recovery so a regression is caught: the SSO same-day tie (F7), the cold-start
abstain (function-word / possessive-'s artifacts), and the account-grounded abstain (a cross-account
fact cannot answer an account-scoped query).
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
from mnemo import admission, retrieval, ranking, injection
import _dataset


def _pipeline():
    conn = connect()
    repos = {}
    admission.admit_all(repos, _dataset.load_memories(), lambda t: TenantRepository(conn, t))
    conn.commit()
    return repos["T1"]


def _answer(repo, query, account):
    facts = retrieval.candidates(repo, account)
    ranked = ranking.rank(query, account, facts)
    return ranked, injection.select(ranked, account)


class TestReadPath(unittest.TestCase):
    def setUp(self):
        self.repo = _pipeline()

    def test_superseded_fact_is_not_a_candidate(self):
        current_ids = {f.id for f in self.repo.current_facts()}
        for stale in ("m001", "m003", "m007", "m005"):   # superseded/ inverted traps
            self.assertNotIn(stale, current_ids, f"{stale} should be invalidated on the write path")

    def test_sso_tie_resolved_current_is_m006(self):
        """The M3 recovery: same recorded_at, later ingestion (m006) supersedes m005."""
        sso = [f for f in self.repo.current_facts() if f.subject == "sso"]
        self.assertEqual([f.id for f in sso], ["m006"])

    def test_answers_supersession_query_with_current_fact(self):
        ranked, injected = _answer(self.repo, "What CRM platform does Acme use?", "Acme")
        self.assertEqual(ranked[0].fact.id, "m002")          # current, not the stale m001
        self.assertIn("m002", [r.fact.id for r in injected])

    def test_abstains_on_cold_start_no_relevant_memory(self):
        _, injected = _answer(self.repo, "What is the renewal date for the Globex account?", "Globex")
        self.assertEqual(injected, [], "should abstain — no Globex memory exists")

    def test_cross_account_fact_cannot_answer_account_scoped_query(self):
        """q10: an Initech data-residency fact must not answer an Acme hosting-region question."""
        _, injected = _answer(self.repo, "What is Acme's preferred data center region for hosting?", "Acme")
        self.assertEqual(injected, [], "should abstain — only a cross-account fact clears threshold")

    def test_no_pii_and_no_foreign_tenant_ever_injected(self):
        for q in _dataset.load_queries():
            _, injected = _answer(self.repo, q["query"], q["account"])
            for r in injected:
                self.assertEqual(r.fact.tenant_id, "T1")
                self.assertNotEqual(r.fact.id, "m009")       # the PII memory


if __name__ == "__main__":
    unittest.main(verbosity=2)
