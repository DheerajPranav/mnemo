"""test_red_team.py — [M5] memory-borne prompt injection (threat T4/R4).

Positive AND negative cases, per handbook §8.3 ("sensitive-data policy is tested with positive and
negative cases" — applied here to the injection policy too). The subtle cases are asserted to
SURVIVE: that is the honest, measured residual, and if a future change silently starts blocking them
we want to know, because the same change would likely start blocking legitimate preferences.
"""
import json
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
from mnemo import admission, injection_guard
import _dataset

CASES_PATH = os.path.join(IMPL, "eval", "red_team_cases.jsonl")


def _cases():
    with open(CASES_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def _rec(case, seq):
    return {"id": case["id"], "tenant": "T1", "tenant_name": "N", "account": "Acme",
            "user": "attacker", "ts": "2026-07-25", "text": case["text"], "status": "x",
            "subject": "chatter", "is_pii": False, "note": ""}


class TestInjectionGuard(unittest.TestCase):
    def test_every_overt_planted_instruction_is_blocked_at_admission(self):
        conn = connect()
        self.addCleanup(conn.close)
        repo = TenantRepository(conn, "T1")
        for i, c in enumerate(_cases()):
            if c["expect"] != "blocked":
                continue
            res = admission.admit(repo, _rec(c, i), seq=i)
            self.assertFalse(res.stored, f"{c['id']} ({c['class']}) was admitted")
            self.assertIn(res.reason, ("injection-blocked", "pii-blocked"))

    def test_benign_control_is_not_over_blocked(self):
        conn = connect()
        self.addCleanup(conn.close)
        repo = TenantRepository(conn, "T1")
        benign = [c for c in _cases() if c["expect"] == "admitted"]
        self.assertTrue(benign)
        for i, c in enumerate(benign):
            res = admission.admit(repo, _rec(c, i), seq=i)
            self.assertTrue(res.stored, f"benign case {c['id']} was wrongly blocked")

    def test_guard_does_not_fire_on_any_legitimate_dataset_memory(self):
        offenders = [m["id"] for m in _dataset.load_memories()
                     if injection_guard.is_blocked(m["text"])]
        self.assertEqual(offenders, [], f"injection guard false-positived on {offenders}")

    def test_subtle_indirect_instructions_survive__documented_residual_R4(self):
        """Measured residual, deliberately asserted so it cannot change silently."""
        conn = connect()
        self.addCleanup(conn.close)
        repo = TenantRepository(conn, "T1")
        survivors = []
        for i, c in enumerate(_cases()):
            if c["expect"] != "survives":
                continue
            if admission.admit(repo, _rec(c, i), seq=i).stored:
                survivors.append(c["id"])
        self.assertEqual(sorted(survivors), ["rt09", "rt10", "rt11"],
                         "the R4 residual changed — update verification/security_report.md")


if __name__ == "__main__":
    unittest.main(verbosity=2)
