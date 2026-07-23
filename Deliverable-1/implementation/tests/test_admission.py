"""test_admission.py — [M2] the write path: PII block leaves no trace; supersession invalidates on write."""
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
from mnemo import admission
import _dataset


def _rec(id, subject, ts, text, tenant="T1", account="Acme"):
    return {"id": id, "tenant": tenant, "tenant_name": "Northwind", "account": account,
            "user": "u_ann", "ts": ts, "text": text, "status": "x", "subject": subject,
            "is_pii": False, "note": ""}


class TestAdmission(unittest.TestCase):
    def setUp(self):
        self.conn = connect()
        self.repo = TenantRepository(self.conn, "T1")

    def test_pii_record_stores_nothing(self):
        rec = _rec("mX", "call_notes", "2025-06-01",
                   "his personal mobile is 555-0142 and he's on chemotherapy")
        before = self.repo.count()
        res = admission.admit(self.repo, rec, seq=0)
        self.assertFalse(res.stored)
        self.assertEqual(res.reason, "pii-blocked")
        self.assertEqual(self.repo.count(), before, "a PII-blocked admit left a row")
        # invariant I2: the retained result carries labels, never the raw text
        self.assertNotIn("555-0142", str(res.pii_entities))

    def test_later_fact_supersedes_earlier_on_write(self):
        admission.admit(self.repo, _rec("m001", "crm", "2025-02-11", "Acme uses Salesforce"), 0)
        admission.admit(self.repo, _rec("m002", "crm", "2026-04-30", "Acme migrated to HubSpot"), 1)
        current_ids = {f.id for f in self.repo.current_facts()}
        self.assertIn("m002", current_ids)
        self.assertNotIn("m001", current_ids, "superseded fact still current — validity not on write path")

    def test_out_of_order_admit_of_stale_fact_is_admitted_already_superseded(self):
        admission.admit(self.repo, _rec("m002", "crm", "2026-04-30", "Acme migrated to HubSpot"), 0)
        res = admission.admit(self.repo, _rec("m001", "crm", "2025-02-11", "Acme uses Salesforce"), 1)
        self.assertTrue(res.admitted_stale)
        current_ids = {f.id for f in self.repo.current_facts()}
        self.assertEqual(current_ids, {"m002"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
