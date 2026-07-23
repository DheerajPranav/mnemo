"""test_pii_gate.py — [M2] invariant I2: the deterministic PII recognizer.

Fires on genuine identifiers + health data; does NOT fire on ordinary GTM facts (budgets, ISO
dates, account names). Over-blocking would silently drop legitimate facts and fail the M3 gate, so
the false-positive tests matter as much as the true-positive ones.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
IMPL = os.path.abspath(os.path.join(HERE, ".."))
for p in (IMPL, os.path.join(IMPL, "gates")):
    if p not in sys.path:
        sys.path.insert(0, p)

from mnemo import pii_gate
import _dataset


class TestPiiRecognizers(unittest.TestCase):
    def test_blocks_personal_phone(self):
        self.assertTrue(pii_gate.is_blocked("his personal mobile is 555-0142 if we need him"))

    def test_blocks_email_ssn_health(self):
        self.assertTrue(pii_gate.is_blocked("reach me at sam.k@acme.com"))
        self.assertTrue(pii_gate.is_blocked("SSN 123-45-6789 on file"))
        self.assertTrue(pii_gate.is_blocked("Sam is on medical leave for chemotherapy"))

    def test_does_not_block_ordinary_gtm_facts(self):
        clean = [
            "Acme's approved deal budget is 60k, signed off by finance.",
            "Acme finished migrating off Salesforce to HubSpot last quarter.",
            "Update from the QBR on 2026-04-30; the old instance is being decommissioned.",
            "Hard requirement: all customer data must stay in the EU.",
        ]
        for c in clean:
            self.assertFalse(pii_gate.is_blocked(c), f"false positive on: {c}")


class TestPiiOverFixedDataset(unittest.TestCase):
    def test_exactly_the_flagged_memory_is_blocked(self):
        """Across the 44 D3 memories, the gate must block precisely the is_pii=True one (m009)."""
        memories = _dataset.load_memories()
        blocked = {m["id"] for m in memories if pii_gate.is_blocked(m["text"])}
        flagged = {m["id"] for m in memories if m["is_pii"]}
        self.assertEqual(blocked, flagged, "PII gate disagrees with the dataset's is_pii labels")
        self.assertEqual(blocked, {"m009"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
