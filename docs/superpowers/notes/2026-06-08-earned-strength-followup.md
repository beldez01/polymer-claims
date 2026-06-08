# Earned-strength follow-up (the 2c reconciliation)

## What the 2c first pass shipped
A real-data `mean_diff` claim declares an apparatus `oracle_ref` (`dose_response_apparatus`),
and `apparatus_oracle_registry()` registers a BENCHMARKED `OracleDossier` for it. When a claim
carries an empirical `StrengthVector`, `verify_stage` caps its goodness axes (magnitude,
evidence_against_null, world_contact, certainty) to the tier ceiling (0.6 for BENCHMARKED;
0.0 if the oracle_ref is declared but unregistered). See `_PROVISIONAL_STRENGTH` and
`apparatus_oracle_registry()` in `src/polymer_claims/exec_adapters.py`, and the
`strength=oracle_cap(...)` lines in `protocol/src/polymer_protocol/verify.py`.

## The tension we discovered (important)
The cap only bites if the claim carries a strength. But a **strength-bearing claim is subject
to the #3a cardinality-scaled selective-inference bar** — more simultaneous hypotheses → a
higher evidentiary bar — while **strength-None claims are exempt**. Empirically: 1 strength-
bearing claim licenses; 3 competing strength-bearing claims are all held PENDING; 3 strength-
None claims all license. So in the LIVE multi-claim node, a *provisional* (asserted) strength
makes real-data claims pile up PENDING and never light up.

Resolution shipped: **live/generated claims use `strength=None`** (default) so they clear the
bar and license (2b's watchable deliverable); the oracle cap is exercised on single
strength-bearing claims in tests. This is also the more honest stance — an *asserted* strength
should NOT let a claim license under many comparisons.

## The rigorous extension — EARNED strength
Derive the `StrengthVector` from the ACTUAL verify result at license time, instead of asserting
it:
- `magnitude` from the standardized effect size of the computed mean difference.
- `evidence_against_null` from the margin over the criterion threshold (later: a real test
  statistic / p-value with n), which is exactly the quantity the selective-inference bar
  corrects — so an EARNED strength can **legitimately clear the cardinality bar** when the
  evidence is genuinely strong, reconciling the oracle cap (#2) with selective inference (#3a).
- `world_contact` from the data provenance (real dataset vs. synthetic).
This is a protocol-layer change (compute strength in/around `verify_stage`'s licensing seam),
THEN apply `oracle_cap`. It generalizes when 2d adds real external data sources.

## Why this matters
With earned strength, the three mechanisms compose correctly: SELECT prices the search
(cardinality), VERIFY earns the strength from data, the oracle tier caps it by apparatus
credibility, and only claims with genuinely strong, multiple-comparisons-surviving evidence
license at high strength. That is the intended end state; the provisional pass is scaffolding.
