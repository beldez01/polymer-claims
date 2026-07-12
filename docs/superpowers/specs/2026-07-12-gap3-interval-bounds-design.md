# GAP-3 — interval/range/bound support on `QuantityLeaf` (design)

**Status:** approved (brainstorm 2026-07-12).
**Governing law:** memory `feedback_ir_monotonic_expansion` — additive-or-nothing, general→core, proven byte-identical.
**Precedent recipe:** Phase-2a `MeasurementContext` (grammar `leaf.py`) — an optional structured field with a
drop-when-None `@model_serializer(mode="wrap")`, byte-identity + hash-stability proven.

## Goal

Give the pure-grammar `QuantityLeaf` an honest way to carry an **interval or a one-sided bound** instead of only
a point `value` (+ optional symmetric `uncertainty`). This is the first core-grammar expansion since 2a, and it is
**data-driven**: the synbio ramp's gap harvest produced 11 new gaps of which **five — GAP-5, GAP-6, GAP-9,
GAP-10, GAP-12 — all reduce to "the leaf cannot hold a range or a bound-direction."** Those five are retired by
this slice.

The lie being fixed: today a stated range ("1–3%", "10–100×", "3–4 layers") or a one-sided floor (">10 weeks",
"CD19 below ~2,000/cell") is forced into a fabricated `value ± symmetric uncertainty` — a made-up point with a
made-up error bar. Honest `low`/`high` bounds eliminate that.

## The representation (decided)

Extend `QuantityLeaf` (grammar `src/polymer_grammar/leaf.py`) with **two new optional fields**:

```python
class QuantityLeaf(_Model):
    kind: Literal["quantity"] = "quantity"
    value: float                              # unchanged — the representative/reported figure
    unit: str | None = None
    uncertainty: float | None = None
    measurement_basis: MeasurementBasis
    formula: str | None = None
    dimension: Dimension | None = None
    context: MeasurementContext | None = None
    low: float | None = None                  # NEW — lower bound, open (None) for a ceiling-only claim
    high: float | None = None                 # NEW — upper bound, open (None) for a floor-only claim
```

Either end may be open (`None`), which is what lets one representation cover every case:

| Case | `low` | `high` | example |
|---|---|---|---|
| point (today's behavior) | None | None | a single measured value |
| closed range | set | set | "1–3%" → low=0.01, high=0.03 |
| floor (one-sided ≥) | set | None | ">10 weeks" → low=10 |
| ceiling (one-sided ≤) | None | set | "below ~2,000/cell" → high=2000 |

`value` remains **required** and is the representative/reported figure that lies *within* the bounds.

## Validators — a new `_bound_discipline` (`@model_validator(mode="after")`)

Added beside the existing `_basis_discipline`. The basis discipline is unchanged; bounds are orthogonal to
measurement basis (a FUNDAMENTAL range in nm and a DERIVED fold-range are both allowed).

1. **Ordering** — if both bounds set, require `low < high`. A zero-width interval (`low == high`) is a point;
   use `value` alone. (Strict `<`.)
2. **Containment** — `value` must lie within any present bound: `low <= value` when `low` is set;
   `value <= high` when `high` is set. Keeps `value` an honest point inside its interval; a pure floor has
   `value == low`.
3. **Spread exclusivity** — if `low` **or** `high` is set, `uncertainty` **must** be `None`. An explicit interval
   and a symmetric ± bar are two encodings of the same spread; carrying both is the two-representations
   anti-pattern the 2a "all-None-`MeasurementContext` rejected" rule was written to prevent.
4. **Point case** — `low == high == None` imposes no new constraint (exactly today's behavior).

## Serializer — extend the existing wrap-serializer

The current `QuantityLeaf._serialize` (`@model_serializer(mode="wrap")`) drops `context` when None. Extend it to
**also drop `low` and `high` when None**, so a boundless leaf serializes byte-identically to the pre-field
grammar (no new keys appear).

```python
@model_serializer(mode="wrap")
def _serialize(self, handler) -> dict:
    data = handler(self)
    for k in ("context", "low", "high"):
        if data.get(k) is None:
            data.pop(k, None)
    return data
```

## Byte-identity + hash-stability (the gate)

Proven the 2a way:
- A `QuantityLeaf` with `low == high == None` serializes **byte-identically** to a pre-field baseline (captured
  before adding the fields), in every dump mode.
- All four existing corpora (methyl / pharmaco / immuno / synthetic-biology) round-trip unchanged.
- Leaves are **not** part of any `content_hash` (established in the 2a Opus review; `claim.py` hashes structure,
  not leaf internals), so DL/MDL and content hashes are stable by construction — a regression test pins this.

## Scope

**Retired by this slice:** GAP-5 (floor/ceiling), GAP-6 (closed range), GAP-9 (order-of-magnitude range stored as
plain bounds), GAP-10 (discrete range stored as plain bounds), GAP-12 (one-sided floor).

**Deliberately deferred — logged, tripwire-armed, NOT built (YAGNI, no consumer):**
- **Log/geometric-scale marker** (GAP-9): a `10–100×` range is multiplicative; its true center is √(10·100) ≈ 31.6,
  not 55. We store honest bounds `[10,100]` now; a `scale: linear|log` tag matters only when code *computes inside*
  the interval (centering/interpolation/sampling), which nothing does today.
- **Discrete-integer marker** (GAP-10): "3–4 gate layers" are integers; stored `[3,4]` as floats. A `discrete: true`
  tag matters only if a consumer interpolates a meaningless 3.5.

Both deferrals are reversible (additive-optional, same shape as `low`/`high`) and each gets an armed `xfail`
tripwire so the need re-surfaces the instant a consumer appears.

## Global constraints (invariants — must hold)

- `grammar/` and `protocol/` stay **pure + numpy-free**. `Corpus` stays at exactly **4** collections.
- Additive + optional only; **byte-identical** when both fields are None (drop-when-None serializer).
- No change to `measurement_basis` discipline, to other leaf variants, or to `content_hash`/DL/MDL structure.

## Plan shape (4 tasks — for writing-plans)

1. **Core grammar:** the two fields + `_bound_discipline` (3 rules) + extended serializer, in
   `grammar/src/polymer_grammar/leaf.py`; grammar unit tests for each validator rule; **byte-identity +
   hash-stability tests** (boundless leaf == pre-field baseline; four-corpora round-trip; leaf-not-in-hash).
2. **Flip the armed tripwire:** re-express the synbio probe claim C3 (`car_threshold_claim`) with
   `low=1e2, high=1e4` (dropping any fabricated uncertainty); flip
   `tests/synbio/test_claims_intervals.py::test_c3_interval_gap` from `xfail(strict)` → passing, and update the
   `test_c3_c4_build_as_derived` assertions to match C3's new bounds. C4 (`endosomal_escape_claim`, a point
   `~0.03`) stays a point unless the source genuinely states a range — do not invent one.
3. **Retire the manifest gaps:** re-express the 5 gap-flagged entries in
   `data/synbio_compendia/manifests/plm-*.json` to use `low`/`high` (drop the fabricated `uncertainty`); flip each
   `schema_fit` from `gap` → `clean`; regenerate the merged universe; mark **GAP-5/6/9/10/12 RESOLVED** in
   `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md` (and arm the deferred log/discrete tripwires).
4. **Finalize:** full gate (grammar + protocol + umbrella suites + ruff), `CONTINUE.md` + memory continuity.

## Testing strategy

- **Validators:** one test per rule, each of which would fail against a broken implementation — ordering
  (`low >= high` rejected), containment (`value` outside bounds rejected), spread-exclusivity (bound + uncertainty
  rejected), and the three positive shapes (floor / ceiling / closed range) building cleanly.
- **Byte-identity:** boundless `QuantityLeaf` serialization == captured pre-field baseline; corpora round-trip.
- **Behavior over implementation:** assert honest bounds survive a build→serialize→reload cycle, not that a
  specific dict key exists.
