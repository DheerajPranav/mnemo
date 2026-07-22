# ADR-002: Adopt LongMemEval's ability taxonomy as the evaluation scaffold, extended for GTM

**Status:** proposed
**Date:** 2026-07-22
**Deliverable:** raised in D2 Week 1; shapes D3 workload and D6 evaluation set.
**Traces to:** capability C10, premise P8, non-negotiable gate "compared with the naive baseline".

## Context
C10 requires a fixed, versioned, reproducible adversarial evaluation set, and baseline comparison
is a handbook non-negotiable gate. Building task *types* from scratch risks a set that only tests
what I already expect. The Week-1 scan found LongMemEval (arXiv:2410.10813, ICLR'25): 500 curated
QAs over scalable chat histories, five abilities including **knowledge updates** (= our F4) and
**abstention** (= our cold-start / no-relevant case), with a reported ~30% accuracy drop for
commercial assistants (evidence the tasks are hard).

## Decision drivers
- Need a credible, externally-grounded task taxonomy fast, to de-risk the whole measurement chain.
- Two of LongMemEval's named abilities map exactly onto two D1 failures.
- But LongMemEval has no cross-tenant (F10) or PII (F11) abilities — the GTM-critical, unrecoverable
  failures.

## Options considered
1. **Hand-author ~20 cases from scratch.** Rejected — tests only anticipated failures; no external
   discipline.
2. **Adopt and run LongMemEval's full harness as-is.** Rejected — imports its coverage *gaps* as
   false confidence; also more integration than needed.
3. **Adopt the taxonomy + a case subset, then extend with GTM-authored cases (chosen).**

## Decision
Adopt LongMemEval's five-ability decomposition and its knowledge-update / abstention case *designs*
as the backbone of the fixed set; author GTM-specific cases it lacks — cross-tenant near-duplicate
(F10) and incidental PII (F11) — on top. Version and seed the set (P8).

## Consequences and trade-offs
- (+) Fast, credible scaffold; imports a failure type (abstention) I would likely under-weight.
- (+) Clear separation: borrowed cases test general memory, authored cases test GTM invariants.
- (−) Must avoid implying LongMemEval coverage extends to isolation/PII — documented explicitly.

## Validation plan
The set is usable only if, on the naive baseline, each ability produces a *measurable spread*
(some pass, some fail). A saturated set (all-pass/all-fail) measures nothing and is rebuilt with
harder cases. Checked in D3.

## Revisit conditions
- Rebuild any ability whose cases saturate on the naive baseline.
- Expand GTM-authored cases as new failure modes surface in D6.
