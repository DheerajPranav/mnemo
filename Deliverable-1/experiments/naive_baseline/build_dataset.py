#!/usr/bin/env python3
"""
build_dataset.py — deterministically construct the fixed, seeded GTM memory dataset for the
Deliverable 3 productive-failure baseline.

Design goals (handbook Section 5.2):
  * cover all six required workload conditions;
  * be adversarial by construction, not by accident (the trap memories are hand-authored so a
    single similarity signal is *forced* to expose F4/F7/F8/F10/F11 and the cold-start case);
  * be reproducible: no randomness except deterministic filler generated from a fixed seed.

Running this rewrites data/memories.jsonl and data/queries.jsonl. Both are committed so the
dataset is fixed even without re-running; this script documents how it was made.

Ground-truth conventions
  memory.status : current | superseded | utterance | pii | filler
  query.gold    : id of the correct CURRENT memory, or "ABSTAIN" (nothing should be injected)
  query.trap    : id of the memory that must NOT win (stale / foreign-tenant / pii), or null
  query.probes  : failure ids from ../reconstruction/failure_analysis.md this case exercises
"""
import json
import os
import random

SEED = 20260722
random.seed(SEED)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

memories = []
queries = []


def mem(id, tenant, tenant_name, account, user, ts, text, status="current",
        subject="", is_pii=False, note=""):
    memories.append({
        "id": id, "tenant": tenant, "tenant_name": tenant_name, "account": account,
        "user": user, "ts": ts, "text": text, "status": status, "subject": subject,
        "is_pii": is_pii, "note": note,
    })


def qry(id, tenant, account, user, query, gold, trap, probes, condition):
    queries.append({
        "id": id, "tenant": tenant, "account": account, "user": user, "query": query,
        "gold": gold, "trap": trap, "probes": probes, "condition": condition,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Tenant T1 = "Northwind" (a customer of the GTM-assistant vendor). User u_ann.
# Account: Acme. This is the primary account with the adversarial supersession cases.
# ─────────────────────────────────────────────────────────────────────────────

# F4 supersession — CRM. Stale fact is phrased with MORE overlap with a natural query
# ("CRM platform ... Salesforce ... Salesforce"); the correction is phrased as a correction,
# with less surface overlap — exactly how a single similarity signal serves the stale one.
mem("m001", "T1", "Northwind", "Acme", "u_ann", "2025-02-11",
    "Acme's CRM platform is Salesforce and their entire sales pipeline routes through Salesforce.",
    status="superseded", subject="crm")
mem("m002", "T1", "Northwind", "Acme", "u_ann", "2026-04-30",
    "Update from the QBR: Acme finished migrating off Salesforce to HubSpot last quarter; the old instance is being decommissioned.",
    status="current", subject="crm")

# F4 supersession — decision maker. Same pattern.
mem("m003", "T1", "Northwind", "Acme", "u_ann", "2025-03-02",
    "The primary contact and decision maker at Acme is Ravi Menon, VP Engineering.",
    status="superseded", subject="dm")
mem("m004", "T1", "Northwind", "Acme", "u_ann", "2026-03-20",
    "Heads up: Ravi has left the company. Going forward Priya Raghavan owns this relationship end to end.",
    status="current", subject="dm")

# F7 out-of-context inversion — SSO. The retrievable utterance asserts the inverse of the
# account's real position; the resolving turn is a separate, lower-overlap chunk.
mem("m005", "T1", "Northwind", "Acme", "u_ann", "2025-05-09",
    "On SSO for the pilot: I don't think we need SSO for the pilot.",
    status="utterance", subject="sso",
    note="inverts out of context; the account actually requires SSO for prod")
mem("m006", "T1", "Northwind", "Acme", "u_ann", "2025-05-09",
    "Fair point on security. Put it in — it's non-negotiable for production.",
    status="current", subject="sso")

# Contradictory budget facts (both retrievable; confidence not represented).
mem("m007", "T1", "Northwind", "Acme", "u_ann", "2025-09-01",
    "Priya mentioned the budget for Acme might land around 40k, but it's not confirmed yet.",
    status="superseded", subject="budget")
mem("m008", "T1", "Northwind", "Acme", "u_ann", "2026-02-15",
    "Acme's approved deal budget is 60k, signed off by finance.",
    status="current", subject="budget")

# F11 incidental PII — stored by default because there is no admission control.
mem("m009", "T1", "Northwind", "Acme", "u_ann", "2025-06-01",
    "Aside on the June call: Priya said her colleague Sam is on medical leave for chemotherapy; "
    "his personal mobile is 555-0142 if we need to reach him directly.",
    status="pii", subject="call_notes", is_pii=True,
    note="health data + personal phone; should never have been admitted")
mem("m010", "T1", "Northwind", "Acme", "u_ann", "2025-06-01",
    "June call: we walked through the integration timeline and next steps on procurement.",
    status="current", subject="call_notes")

# ─────────────────────────────────────────────────────────────────────────────
# Tenant T1, account Initech — long conversation with one buried dealbreaker (F2/F3/F8).
# The residency dealbreaker is stated once, early; the rest of the thread is lower-stakes.
# ─────────────────────────────────────────────────────────────────────────────
mem("m020", "T1", "Northwind", "Initech", "u_ann", "2026-01-05",
    "Kickoff with Initech. Hard requirement from their legal: all customer data must stay resident "
    "in the EU; they will not approve anything that stores data outside the EU.",
    status="current", subject="residency",
    note="the single dealbreaker, stated once, early — the case for importance-aware selection")
initech_thread = [
    "We introduced the team and shared the mutual action plan.",
    "Discussed the integration with their existing ticketing system.",
    "They asked about SSO options and SCIM provisioning.",
    "Walked through the reporting dashboards and export formats.",
    "Talked through the pilot success criteria and timeline.",
    "They want a sandbox environment before signing.",
    "Reviewed the security questionnaire; mostly standard controls.",
    "Pricing discussion: they pushed for an annual discount.",
    "Agreed to a follow-up with their procurement team next week.",
    "Scheduling: let's aim for Tuesday at 10am their time.",
    "Thanks all, good session — talk soon.",
    "Quick follow-up: they liked the analytics preview.",
]
for i, t in enumerate(initech_thread, start=1):
    mem(f"m0{20 + i}", "T1", "Northwind", "Initech", "u_ann", "2026-01-05",
        f"Initech thread turn {i}: {t}", status="filler", subject="thread")

# ─────────────────────────────────────────────────────────────────────────────
# Tenant T2 = "Contoso" (a DIFFERENT customer of the vendor) — also has an account called
# "Acme". Notes are lexically near-identical to T1's. No index-level isolation in the naive
# baseline, so a T1 query can pull these back (F10 cross-tenant leakage).
# ─────────────────────────────────────────────────────────────────────────────
mem("m101", "T2", "Contoso", "Acme", "u_bob", "2026-01-15",
    "Acme's CRM platform is Salesforce and their entire sales pipeline routes through Salesforce.",
    status="current", subject="crm",
    note="near-duplicate of m001 but a different tenant; retrieving it for T1 is a leak")
mem("m102", "T2", "Contoso", "Acme", "u_bob", "2026-01-16",
    "The primary contact and decision maker at Acme is Dana Whitfield, Head of Procurement.",
    status="current", subject="dm", note="foreign-tenant decision maker; leak if returned to T1")
mem("m103", "T2", "Contoso", "Acme", "u_bob", "2026-01-20",
    "Acme's approved deal budget is 85k for the Contoso engagement.",
    status="current", subject="budget", note="foreign-tenant budget; commercially confidential")

# ─────────────────────────────────────────────────────────────────────────────
# Deterministic filler / duplicates → index saturation and storage growth (F8).
# Repeated recitations of the same low-value fact from many calls, plus scheduling chatter.
# ─────────────────────────────────────────────────────────────────────────────
chatter = [
    "Thanks, talk soon!",
    "Let's schedule the next call.",
    "Appreciate the time today.",
    "Following up on my last note.",
    "Sounds good, will circle back.",
    "Great chatting, have a good week.",
]
for i in range(1, 13):
    acct = random.choice(["Acme", "Initech"])
    txt = random.choice(chatter)
    mem(f"f{i:03d}", "T1", "Northwind", acct, "u_ann", "2025-1%d-0%d" % (i % 2 + 1, i % 9 + 1),
        f"{txt}", status="filler", subject="chatter")
# duplicate recitations of the (stale) Salesforce fact across six calls — crowds top-k
for i in range(1, 7):
    mem(f"d{i:03d}", "T1", "Northwind", "Acme", "u_ann", "2025-0%d-10" % (i + 1),
        "Reminder from the call: Acme's CRM platform is Salesforce; pipeline routes through Salesforce.",
        status="filler", subject="crm",
        note="duplicate of the stale m001 fact; inflates its apparent support")

# ─────────────────────────────────────────────────────────────────────────────
# Evaluation queries. Each is issued in a tenant/account context and names its gold + trap.
# ─────────────────────────────────────────────────────────────────────────────

# Condition 1: preferences that change over time (F4 supersession)
qry("q01", "T1", "Acme", "u_ann", "What CRM platform does Acme use?",
    gold="m002", trap="m001", probes=["F4"], condition="supersession")
qry("q02", "T1", "Acme", "u_ann", "Who is the primary contact and decision maker at Acme?",
    gold="m004", trap="m003", probes=["F4"], condition="supersession")
qry("q03", "T1", "Acme", "u_ann", "What is Acme's approved budget for the deal?",
    gold="m008", trap="m007", probes=["F4"], condition="supersession/contradiction")

# Condition: chunk inverts out of context (F7)
qry("q04", "T1", "Acme", "u_ann", "Does Acme need SSO?",
    gold="m006", trap="m005", probes=["F7"], condition="out-of-context-inversion")

# Condition 4: multiple tenants with similar wording → cross-tenant leakage (F10)
qry("q05", "T1", "Acme", "u_ann", "What CRM platform does Acme use? (issued by Northwind/T1)",
    gold="m002", trap="m101", probes=["F4", "F10"], condition="cross-tenant-near-duplicate")
qry("q06", "T1", "Acme", "u_ann", "Who is the decision maker at Acme? (issued by Northwind/T1)",
    gold="m004", trap="m102", probes=["F10"], condition="cross-tenant-near-duplicate")

# Condition 5: sensitive info that should not be retained (F11)
qry("q07", "T1", "Acme", "u_ann", "What did we discuss on the Acme June call?",
    gold="m010", trap="m009", probes=["F11"], condition="pii-should-not-surface")

# Condition 3: long conversation with a constrained budget — buried dealbreaker (F2/F3/F8)
qry("q08", "T1", "Initech", "u_ann", "Are there any hard requirements or dealbreakers for Initech?",
    gold="m020", trap=None, probes=["F3", "F8"], condition="long-context-buried-fact")

# Condition 6: cold start / no relevant memory → should ABSTAIN
qry("q09", "T1", "Globex", "u_ann", "What is the renewal date for the Globex account?",
    gold="ABSTAIN", trap=None, probes=["cold-start"], condition="cold-start-no-relevant")
qry("q10", "T1", "Acme", "u_ann", "What is Acme's preferred data center region for hosting?",
    gold="ABSTAIN", trap=None, probes=["cold-start"], condition="no-relevant-memory")

# Condition 1 (irrelevant + contradictory both retrievable): a query whose top-k will mix
# the current fact with stale duplicates (F8 wasted slots).
qry("q11", "T1", "Acme", "u_ann", "Tell me about Acme's CRM and pipeline setup.",
    gold="m002", trap="m001", probes=["F4", "F8"], condition="index-saturation")


def write_jsonl(path, rows):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    write_jsonl(os.path.join(DATA, "memories.jsonl"), memories)
    write_jsonl(os.path.join(DATA, "queries.jsonl"), queries)
    n_pii = sum(1 for m in memories if m["is_pii"])
    n_t2 = sum(1 for m in memories if m["tenant"] == "T2")
    print(f"seed={SEED}")
    print(f"wrote {len(memories)} memories ({n_pii} PII, {n_t2} foreign-tenant), "
          f"{len(queries)} queries")
