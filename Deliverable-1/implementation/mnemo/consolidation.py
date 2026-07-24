"""
consolidation.py — rollups that CITE their sources and never replace them. [M4]

Invariant **I8**. The failure this exists to prevent is F5 (loss on summarisation) / F6 (drift): the
naive move is to summarise N memories into one and drop the N. Then the detail is gone, the summary
slowly diverges from the truth, and nothing can be re-derived.

Two rules make that impossible here:
  1. the rollup is written under a DISTINCT subject (`<subject>#rollup`), so it can never collide with
     its sources under the M2 supersession rule and therefore can never invalidate them;
  2. every source is linked by a `consolidation_edge`, so the rollup is re-derivable — `rederive()`
     returns the exact source facts it was built from, and each stays independently retrievable.

Consolidation is additive. It never deletes, never invalidates, and never rewrites a source.
"""

ROLLUP_SUFFIX = "#rollup"


def rollup_subject(subject):
    return f"{subject}{ROLLUP_SUFFIX}"


def is_rollup(fact):
    return fact.subject.endswith(ROLLUP_SUFFIX)


def consolidate(repo, *, account, subject, rollup_id, summary_text, at, seq):
    """Create a rollup over this tenant's currently-valid facts for (account, subject).

    Returns (rollup_id, [source_ids]). Sources are left untouched — verify with `repo.current_facts()`.
    """
    sources = [f for f in repo.current_facts(account=account)
               if f.subject == subject and not is_rollup(f)]
    if not sources:
        return rollup_id, []

    repo.add_fact(
        id=rollup_id, account=account, subject=rollup_subject(subject),
        mem_type="fact", text=summary_text, recorded_at=at, seq=seq,
        provenance=f"consolidation of {len(sources)} sources",
    )
    repo.add_embedding(rollup_id, " ".join(sorted(set(summary_text.lower().split()))))

    for s in sources:
        repo.add_consolidation_edge(consolidated_id=rollup_id, source_id=s.id, at=at)

    return rollup_id, [s.id for s in sources]


def rederive(repo, rollup_id):
    """The source facts a rollup cites — proof the summary is re-derivable, not a replacement."""
    return repo.sources_for(rollup_id)
