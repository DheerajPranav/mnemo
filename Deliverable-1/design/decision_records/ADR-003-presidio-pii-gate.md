# ADR-003: Presidio-based PII gate at admission (deterministic-first), with deletion as backstop

**Status:** proposed
**Date:** 2026-07-22
**Deliverable:** raised in D2 Week 1; binds D4 threat model + D6 admission implementation.
**Traces to:** capability C2/C8, failure F11, premise P6.

## Context
`failure_analysis.md` D-6 argues PII must be caught at *admission*, never as an output filter,
because by output time the data is already in the store, the index, and backups. D1 left the
mechanism unspecified. The Week-1 scan selected Microsoft Presidio (OSS): deterministic recognizers
(regex + checksum validators) plus optional NER, with confidence scores and an anonymizer.

## Decision drivers
- F11 is an unrecoverable failure (legal). It needs a *tested* control, not a policy statement —
  D6 requires positive + negative PII cases.
- Keeping an LLM off the PII-critical path lowers cost/latency and removes a prompt-injection surface.

## Options considered
1. **LLM classifier for PII.** Flexible but costly, non-deterministic, and adds injection surface
   on a critical path. Rejected as the primary gate.
2. **Regex-only.** Cheap, catches structured PII (cards/emails/phones) but misses names/locations.
3. **Presidio deterministic-first, NER optional (chosen).**

## Decision
Adopt Presidio at admission: run deterministic recognizers on every candidate before any write;
treat NER recognizers as configurable add-ons measured for recall/cost. **Deletion (C7) remains the
backstop** for residual false negatives — the gate is defence-in-depth, not a sole guarantee.

## Consequences and trade-offs
- (+) Deterministic, testable, fast; converts F11 from policy into a measured control.
- (+) No LLM on the PII path.
- (−) Recognizer recall is imperfect; residual PII possible → deletion backstop is mandatory, not
  optional.
- (−) NER recognizers add latency/cost; gated behind measurement.

## Validation plan
Labelled PII positive/negative case set in D6; report gate precision and recall. Negative cases
(non-PII that must *not* be blocked) guard against over-blocking that would starve the store.

## Revisit conditions
- If measured recall is too low for the risk tolerance, add targeted recognizers or a lightweight
  secondary check — but never remove the deletion backstop.
- If over-blocking harms recall of legitimate memories, tune recognizer confidence thresholds.
