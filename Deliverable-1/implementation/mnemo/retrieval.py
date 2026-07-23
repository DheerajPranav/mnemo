"""
retrieval.py — candidate fetch for the read path. [M3]

The single most important line in the whole system: candidates come from `repo.current_facts()`,
which is BOTH tenant-scoped (I1) AND validity-filtered (I3). So by the time a fact reaches the
ranker it is guaranteed tenant-local and currently-valid — a superseded or foreign fact was never a
candidate. The read path cannot re-introduce F4/F10; those were closed upstream (write path + repo).

`account` is a *soft* signal handed to the ranker, not a hard filter: a genuinely relevant fact about
a related account can still surface, but same-account facts are grounded up. Cold-start correctness
therefore rests on the abstain threshold (injection.py), not on an account WHERE clause.
"""


def candidates(repo, account=None):
    """Currently-valid, tenant-scoped facts. (account kept for signature symmetry; grounding is
    applied in ranking, so we pass the full valid set through.)"""
    return repo.current_facts()
