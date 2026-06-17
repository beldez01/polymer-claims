# Earned strength — the full 2c reconciliation (design)

**Date:** 2026-06-08
**Status:** shipped to `main` (design approved 2026-06-08); live state in `docs/superpowers/CONTINUE.md`
**Predecessor:** `docs/superpowers/archive/specs/2026-06-08-phase2bc-real-data-generation-and-oracle-design.md` +
`docs/superpowers/notes/2026-06-08-earned-strength-followup.md`
**Layer:** protocol (pure) + a tiny umbrella seam adjustment; **zero grammar changes**

---

## Problem

The 2c first pass capped an *asserted* empirical `StrengthVector` by the apparatus oracle tier
(`apparatus_oracle_registry()` → BENCHMARKED → 0.6) at `verify_stage`. But it discovered a
tension:

- The oracle cap only bites if the claim **carries** a strength.
- A strength-bearing claim is subject to the **#3a cardinality-scaled selective-inference bar**
  (`_permitted_by_bar`): more simultaneous hypotheses → higher evidentiary bar.
- A `strength=None` claim is **exempt** from that bar.

So in the live multi-claim node, an *asserted* provisional strength makes real-data claims pile
up PENDING and never light up. The scaffolding resolution was to emit `strength=None` for
live/generated claims (exempt → they license) and exercise the oracle cap only on single
strength-bearing claims in tests. That is scaffolding, not the end state.

## The reconciliation

Stop **asserting** a strength for an apparatus-grounded empirical claim. **Earn** it from the
actual verify result, at the licensing seam. The earned `evidence_against_null` then feeds the
selective-inference bar, so genuinely-strong real evidence **legitimately clears** the
cardinality penalty — and the oracle tier still caps the **recorded** strength afterward. The
three mechanisms then compose as intended:

> SELECT prices the search (cardinality) · VERIFY earns the strength from data · the oracle tier
> caps it by apparatus credibility.

## Decisions (locked)

**D1 — Cap ordering: raw earned → bar, cap after.** `_permitted_by_bar` scores the **raw
(uncapped) earned** `evidence_against_null`. The oracle cap is applied to the **recorded**
strength *after* the licensing decision (`cap_strength(earned, tier)`). Rationale: data-evidence
survives selection on its own merit; apparatus credibility limits the strength a claim is
*allowed to record*, not whether the data clears multiple-comparisons correction. Already-LICENSED
claims are not re-executed, so the recorded (capped) strength is never re-tested by the bar → no
oscillation.

**D2 — Scope: `strength is None` + `oracle_ref` only.** A claim is moved onto the earned path
at verify iff ALL hold:
  1. `c.strength is None` (the builder default — unchanged),
  2. `c.evaluation_plan` references at least one `oracle_ref`,
  3. it executed this cycle to an **agreed, numeric** terminal value with a **SATISFIED** verdict.

Everything else is byte-unchanged:
  - `builtin::const` claims (no `oracle_ref`) → still exempt (`strength` stays `None`).
  - Claims arriving **with** an asserted strength → still the asserted path + `oracle_cap` (the
    existing `test_benchmarked_oracle_caps…` / unvalidated tests stay green). Asserted strength
    remains an explicit escape hatch that still goes through the bar (an asserted
    `evidence_against_null` is scored, never exempted).

## Derivation (pure, protocol-layer, no I/O)

New pure helper (protocol):

```
earn_strength(
    value: float,
    criterion: SatisfactionCriterion,
    *,
    has_real_data: bool,
    agreement: bool,
) -> StrengthVector
```

Derived only from what `verify_stage` actually has — the agreed terminal `value` and the
criterion's `comparator` + `threshold`. **n / SD / a real test statistic are NOT available** in
the exec record and are explicitly deferred (they require the adapter to emit n+SD — a 2d-adjacent
follow-up).

- **Signed margin over threshold** (the criterion passed, so this is ≥ 0 by construction):
  - GT/GE: `margin = value - threshold`
  - LT/LE: `margin = threshold - value`
  - EQ/NE and any non-ordering comparator: margin treated as 0 (no earned evidence beyond the
    base) — earned `evidence_against_null` falls to the floor; such a claim simply won't clear a
    competitive bar. (mean_diff uses GT, so this is a defensive branch.)
  - `scale = max(|threshold|, EPS)`; `rel_margin = margin / scale` (clamped ≥ 0).
- **Saturating squash** `sat(x) = 1 - exp(-K * x)` maps an unbounded non-negative ratio into
  `[0, 1)`. One shared shape constant `K` (calibrated in the plan/tests so the bundled true effect
  — high−low = 14.0 vs threshold 10.0, `rel_margin = 0.4` — clears the live seed's bar; a thin
  margin does not). `K` lives as a named module constant with a comment, tunable.
- **Axes:**
  - `evidence_against_null = sat(rel_margin)`
  - `magnitude            = sat(|value| / scale)`
  - `world_contact        = 0.9 if has_real_data else 0.3`  (executed against a real `DataHandle`)
  - `certainty            = 0.8 if agreement else 0.4`       (two independent impls agreed)
  - `severity             = 0.7`  (theory axis — a pre-registered threshold met by real
                                   computation is a genuine severe test; uncapped)
  - `explanatory_virtue   = 0.5`  (theory axis — neutral, no theory argument supplied; uncapped)

  The exact float defaults for the theory axes and the `0.9/0.3`, `0.8/0.4` pairs are v1 and
  tunable; only `evidence_against_null` and `magnitude` are derived continuously from the result.

`has_real_data` = the plan has ≥1 `DataHandle` input on any node. `agreement` = `ev.agreement`.

## Wiring in `verify_stage`

1. Build an `earned: dict[str, StrengthVector]` map up front: for each executed claim meeting D2,
   `earned[c.id] = earn_strength(terminal_value, criterion, has_real_data=…, agreement=…)`.
   (Terminal value = `ev.results[0].terminal.value`, valid because agreement is required and the
   value is numeric; the SATISFIED verdict is already implied by the existing
   `ev.satisfaction is not None` licensing precondition, but the earned map is built only for
   numeric/agreed/satisfied executed claims.)
2. `_permitted_by_bar(corpus, exec_records, earned)`: when an executed claim has an entry in
   `earned`, the bar scores `1.0 - earned[c.id].evidence_against_null` (the **raw** earned value)
   instead of treating it as exempt. Claims with no earned entry keep today's behavior
   (`strength is None` → exempt; asserted strength → scored from `c.strength`).
3. In the licensing block, the recorded strength is:
   - `cap_strength(earned[c.id], weakest_tier(...))` for earned claims (D1 — cap after),
   - `oracle_cap(c, registry)` for asserted-strength claims (unchanged),
   - `None` for claims with neither (unchanged).
   The MDL-route revision branch uses the same earned-or-`oracle_cap` resolution.

`_permitted_by_bar` keeps its existing defense-in-depth `m = max(m, len(scored))` denominator; an
earned claim is now part of `scored`, so it is counted in the denominator — correct (it IS one of
the simultaneous hypotheses).

## What stays put

- **Grammar:** untouched. `StrengthVector`, `cap_strength`, `weakest_tier`, the criterion IR — all
  reused as-is. Corpus stays at 4.
- **The builder** `mean_diff_claim(... strength=None)` default: unchanged. Earning happens at
  verify, not construction. `_PROVISIONAL_STRENGTH` stays for the single-claim asserted cap tests.
- **`oracle_cap` / `oracle.py`:** unchanged — still used for the asserted path; `cap_strength` is
  reused directly for the earned path.

## Testing

Protocol (pure, no network/IO):
- `earn_strength` unit table: GT margin → monotone `evidence_against_null`; larger margin → higher
  evidence; zero/negative margin → floor; LT mirrored; non-ordering comparator → floor; `magnitude`
  scales with `|value|`; `has_real_data` / `agreement` toggle their axes.
- `verify_stage` earned path, single claim: a None-strength + oracle_ref claim that executes to a
  strong margin **licenses**, records a strength whose goodness axes are **capped to the tier**
  (BENCHMARKED → ≤ 0.6) while the theory axes (severity/explanatory_virtue) are uncapped.
- `verify_stage` reconciliation, multi-claim: among several competing None-strength + oracle_ref
  claims, the strongly-supported one(s) **clear the bar and license**; a thin-margin rival is
  **held PENDING** (correct selective-inference behavior) — demonstrating earned evidence pricing
  the search.
- Regression: a `builtin::const` None-strength claim is byte-unchanged (exempt, `strength` stays
  `None`); an **asserted**-strength oracle_ref claim still licenses with the `oracle_cap` 0.6 result
  (existing `test_benchmarked_oracle_caps…` unchanged).

Umbrella:
- The live seed (`real_data_seed_corpus`) drives `run_cycle`/the node: at least one earned
  real-data claim reaches LICENSED with a tier-capped earned strength (the watchable 2b deliverable
  survives the move off the exempt path). Calibrate `K` so seed-md-1 (margin 0.4) clears at the
  seed's cardinality.

Gates: `protocol` + `grammar` + umbrella pytest green; isolation (grammar imports nothing from
protocol); `scripts/check-all.sh` + install-smoke green.

## Honesty caveat (carried forward)

Earned evidence here is the **margin over a pre-registered threshold**, not a p-value with n.
That is a real, data-derived quantity (it moves with the computed effect), but it is not yet a
calibrated statistical test. The n/SD/test-statistic enrichment — which would let
`evidence_against_null` be a true selective-inference-corrected p-value — is deferred to the 2d arc
(real external data sources on the same `Adapter` seam, where the adapter can emit n+dispersion).

## Out of scope

- Adapter-emitted n / SD / test statistic (2d follow-up).
- PolymerGenomicsAPI as a second data source (Phase 2d).
- The `stats::mean_diff` viewer card computed-value/✓✗ gap (separate viewer/endpoint follow-up).
- The standalone `strength.py` uncertainty-polarity rename (independent, user-gated).
