# ADR-001: Bi-temporal validity and supersession-by-invalidation as the memory representation

**Status:** proposed (accept pending Deliverable 3 falsification test)
**Date:** 2026-07-22
**Deliverable:** raised in D2 Week 1; binds D4 design; validated in D3.
**Traces to:** capability C3/C5/C7, failure F4, premise P4 (`../../reconstruction/first_principles.md`).

## Context
Deliverable 1 derived (P4 → C3) that a memory is "a proposition + a time interval + a supersession
relation," and `failure_analysis.md` D-1 showed similarity ranking structurally cannot express
validity. The Week-1 scan found external evidence (Zep/Graphiti, arXiv:2501.13956) that a
**bi-temporal** model with edge **invalidation** materially improves temporal handling
(up to +18.5% LongMemEval; DMR 94.8% vs 93.4% vs MemGPT). This ADR pins the concrete representation.

## Decision drivers
- F4 (superseded fact served as current) is the failure on which the justification for the most
  important component, C5 multi-signal ranking, rests (`first_principles §6` falsifier 1).
- Deletion and audit (C4, C7, F9) need history preserved, not overwritten.
- v1 non-goal: hand-specified, inspectable structure — no heavy new infrastructure.

## Options considered
1. **Recency weight in the ranker only.** Cheapest. Rejected as *sole* fix: expresses
   newer-is-better, not supersession; an old-but-still-valid fact loses to a newer noisy utterance.
2. **Full temporal knowledge graph (adopt Graphiti wholesale).** Strongest mechanism, but a large
   operational surface and it conflicts with the v1 inspectable-structure non-goal.
3. **Bi-temporal fields + invalidation on the typed fact (chosen).** Each fact carries valid-from /
   valid-to (world time) and recorded-at / invalidated-at (system time); a contradicting fact sets
   the prior fact's valid-to + invalidated-at rather than deleting it. Retrieval filters to
   currently-valid facts. Conflict resolution moves to the write path (see ADR consequence).

## Decision
Adopt **option 3**. Additionally, **relocate conflict resolution from the ranker to the write path**
(backlog B-005): the ranker orders only currently-valid facts; supersession is handled at admission
by invalidation. Adopt the *model and semantics* from Zep, **not** the Graphiti engine.

## Consequences and trade-offs
- (+) F4 becomes a representational guarantee rather than a ranking hope; ranking simplifies.
- (+) History preserved → serves audit (C9) and re-derivation; deletion (C7) still authoritative.
- (−) Requires contradiction detection at admission, which can be wrong; an incorrectly invalidated
  fact silently drops out of retrieval. This is D1 open question 2, now load-bearing.
- (−) Adds schema fields and a write-path comparison step (low runtime cost — a field compare, no
  model call for the temporal filter itself).

## Validation plan
Deliverable 3, three-arm comparison on the fixed adversarial set: (i) naive similarity, (ii)
similarity + recency, (iii) validity-filtered retrieval. Metric: rate at which a superseded
preference outranks / is served over the current one.

## Revisit conditions
- **Reverse** if arm (ii) similarity+recency matches arm (iii) validity-filter on the fixed set
  (then P4 does not force this in practice; downgrade to `defer`).
- **Revisit** contradiction-detection precision if D6 shows incorrect invalidations above a
  tolerable rate; consider inject-both-with-dates (D1 open question 2) as a fallback.
