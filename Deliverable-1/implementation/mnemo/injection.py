"""
injection.py — budgeted, de-duplicated, account-grounded, abstaining context selection. [M3]

Invariant **I4**: injected context never exceeds TOKEN_BUDGET, and when nothing clears the abstain
threshold the system returns NOTHING rather than padding the window with filler (closes F8 wasted
slots and the cold-start "answer anyway" failure). The baseline had no threshold and no dedup.

Abstain is decided on raw lexical relevance (`Ranked.lexical`) of the best *same-account* candidate:
a fact about a DIFFERENT account is not evidence about the queried account, so it cannot, on its own,
keep the system from abstaining. This is what makes cold-start correct even when a cross-account fact
shares a content word — e.g. q10 asks about Acme's hosting region; the only fact clearing threshold is
an Initech data-residency fact, so the system abstains (M3 recovery — see checkpoints/M3.md).
"""

TOKEN_BUDGET = 2000       # Deliverable-1 constraint (<=2000 of a 16k window)
ABSTAIN_THRESHOLD = 0.10  # same reference threshold the D3 baseline defined but never applied


def estimate_tokens(text):
    """~1.3 tokens per whitespace word — the same deterministic estimate the baseline used, so
    budget accounting is comparable across the two systems."""
    return int(round(len(text.split()) * 1.3))


def select(ranked, account, token_budget=TOKEN_BUDGET, abstain_threshold=ABSTAIN_THRESHOLD):
    """Return the facts to inject (possibly empty = abstain).

    - abstain unless at least one SAME-ACCOUNT candidate's lexical relevance clears the threshold
      (a cross-account fact cannot answer an account-scoped query on its own);
    - otherwise walk best-first, keep one fact per (account, subject) slot (dedup), inject only facts
      that clear the threshold, and stop before the token budget would be exceeded.
    """
    grounded = [r for r in ranked
                if r.fact.account == account and r.lexical >= abstain_threshold]
    if not grounded:
        return []  # no same-account evidence → abstain

    injected, used, seen = [], 0, set()
    for r in ranked:
        if r.lexical < abstain_threshold:
            continue
        key = (r.fact.account, r.fact.subject)
        if key in seen:
            continue
        cost = estimate_tokens(r.fact.text)
        if used + cost > token_budget:
            break
        injected.append(r)
        used += cost
        seen.add(key)
    return injected
