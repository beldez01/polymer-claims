# GAP-3 Interval/Range/Bound (low/high on QuantityLeaf) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the pure-grammar `QuantityLeaf` optional `low`/`high` bounds (either end open) so a claim can carry an honest interval or one-sided bound instead of a fabricated `value ± symmetric uncertainty`, and re-express the five interval-family synbio claims that demanded it.

**Architecture:** Additive-and-optional, byte-identical when boundless (drop-when-None wrap-serializer, mirroring the Phase-2a `MeasurementContext` recipe). Two new fields + one `_bound_discipline` validator on `QuantityLeaf`; the umbrella manifest pipeline (`ManifestLeaf`, `build_claim`) is extended to carry the fields; the five gap-flagged manifest entries and the C3 probe claim are re-expressed; deferred log/discrete markers are logged with armed tripwires.

**Tech Stack:** Python 3.12, pydantic v2, the existing grammar kernel. numpy-free. Spec: `docs/superpowers/specs/2026-07-12-gap3-interval-bounds-design.md`.

## Global Constraints

- `grammar/` and `protocol/` stay **pure + numpy-free**. `Corpus` has **exactly 4 collections** — never add one.
- New leaf fields are **additive + optional**; a `QuantityLeaf` with `low == high == None` must serialize **byte-identically** to the pre-field grammar (drop-when-None serializer). All existing corpora (methyl/pharmaco/immuno/synthetic-biology) round-trip unchanged.
- No change to `measurement_basis` discipline, to other leaf variants, or to `description_length`/DL-MDL structure.
- Every synbio claim stays `CONJECTURED` / `LITERATURE_EXTRACTED`; nothing self-licenses.
- **Representative-value rule** (used in Task 4): when re-expressing a claim whose original `value` was a fabricated midpoint of a range, set `value = low` (the honest lower bound). This sidesteps the deferred geometric/discrete-center question. For a one-sided floor, `value == low` already.
- Test commands: grammar `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -q`; umbrella `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/synbio/ -v`; full umbrella `uv run --project . pytest tests/ -q` (SLOW ~13min — real pharmaco scan; use targeted during iteration).

---

## File Structure

- `grammar/src/polymer_grammar/leaf.py` — `QuantityLeaf` gains `low`/`high` + `_bound_discipline`; serializer extended (Task 1).
- `grammar/tests/test_leaf_bounds.py` — new; validator + byte-identity + DL-stability tests (Task 1).
- `src/polymer_claims/synbio/claims.py` — C3 `car_threshold_claim` re-expressed with bounds (Task 2).
- `tests/synbio/test_claims_intervals.py` — flip the armed C3 tripwire; add deferred-marker tripwires (Tasks 2, 4).
- `src/polymer_claims/synbio/manifest.py` — `ManifestLeaf` gains `low`/`high` (Task 3).
- `src/polymer_claims/synbio/ingest.py` — `build_claim` threads `low`/`high` into `QuantityLeaf` (Task 3).
- `data/synbio_compendia/manifests/plm-{02,03,06,07}-*.json` — five entries re-expressed (Task 4).
- `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md` — GAP-5/6/9/10/12 marked RESOLVED (Task 4).
- `viewer/public/merged-universe.json` — regenerated (Task 4).
- `docs/superpowers/CONTINUE.md` + memory — continuity (Task 5).

---

### Task 1: Core grammar — `low`/`high` fields, `_bound_discipline`, drop-when-None serializer

**Files:**
- Modify: `grammar/src/polymer_grammar/leaf.py` (the `QuantityLeaf` class, lines ~53-83)
- Test: `grammar/tests/test_leaf_bounds.py` (create)

**Interfaces:**
- Produces: `QuantityLeaf(..., low: float | None = None, high: float | None = None)` with a `_bound_discipline` validator; the existing `_serialize` wrap-serializer also drops `low`/`high` when None.

- [ ] **Step 1: Write the failing tests** (`grammar/tests/test_leaf_bounds.py`):

```python
"""GAP-3 — optional low/high bounds on QuantityLeaf (interval/range/one-sided bound).

Load-bearing property is BYTE-IDENTITY: a boundless QuantityLeaf must serialize exactly as it
did before the fields existed (no new key), so every existing corpus is unaffected.
"""
import pytest
from pydantic import ValidationError

from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf

# Captured from the pre-change grammar (the byte-identity baseline — must stay exact).
_FUND_BASELINE = (
    '{"kind":"quantity","value":2.0,"unit":"kcal/mol","uncertainty":1.0,'
    '"measurement_basis":"fundamental","formula":null,"dimension":null}'
)


def test_boundless_leaf_is_byte_identical():
    f = QuantityLeaf(
        value=2.0, unit="kcal/mol", uncertainty=1.0,
        measurement_basis=MeasurementBasis.FUNDAMENTAL,
    )
    assert f.model_dump_json() == _FUND_BASELINE       # no "low"/"high" keys leak
    assert "low" not in f.model_dump() and "high" not in f.model_dump()


def test_floor_bound_builds_and_round_trips():
    # one-sided floor: ">10 weeks" -> low=10, high open, value==low
    leaf = QuantityLeaf(
        value=10.0, unit="weeks", measurement_basis=MeasurementBasis.FUNDAMENTAL, low=10.0,
    )
    dumped = leaf.model_dump_json()
    assert '"low":10.0' in dumped and '"high"' not in dumped
    back = QuantityLeaf.model_validate_json(dumped)
    assert back.low == 10.0 and back.high is None


def test_ceiling_bound_builds():
    leaf = QuantityLeaf(
        value=2000.0, unit="molecules/cell", measurement_basis=MeasurementBasis.FUNDAMENTAL, high=2000.0,
    )
    assert leaf.high == 2000.0 and leaf.low is None


def test_closed_range_builds():
    leaf = QuantityLeaf(
        value=10.0, measurement_basis=MeasurementBasis.DERIVED, formula="dynamic_range",
        low=10.0, high=100.0,
    )
    assert leaf.low == 10.0 and leaf.high == 100.0


def test_ordering_rejected_when_low_not_less_than_high():
    with pytest.raises(ValidationError, match="low < high"):
        QuantityLeaf(value=5.0, measurement_basis=MeasurementBasis.DERIVED, formula="f",
                     low=5.0, high=5.0)


def test_containment_rejected_value_below_low():
    with pytest.raises(ValidationError, match="below low bound"):
        QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f",
                     low=10.0, high=100.0)


def test_containment_rejected_value_above_high():
    with pytest.raises(ValidationError, match="above high bound"):
        QuantityLeaf(value=200.0, measurement_basis=MeasurementBasis.DERIVED, formula="f",
                     low=10.0, high=100.0)


def test_spread_exclusivity_bound_plus_uncertainty_rejected():
    with pytest.raises(ValidationError, match="two spread encodings"):
        QuantityLeaf(value=10.0, uncertainty=1.0, measurement_basis=MeasurementBasis.DERIVED,
                     formula="f", low=10.0, high=100.0)
```

> **DL/MDL stability is structural-by-construction, no dedicated test needed:** `description_length.py`'s
> `_n_structural_slots(claim)` counts a `QuantityLeaf` via `isinstance` only — it never reads `value`/`low`/`high`,
> so bounds cannot change the count. The existing `grammar/tests/test_description_length.py` staying green in Step 5
> confirms this; do not add a redundant DL test.

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_leaf_bounds.py -v`
Expected: FAIL — `QuantityLeaf` has no `low`/`high` (pydantic rejects unknown kwargs) and the validators don't exist. Confirm the DL helper's real name here.

- [ ] **Step 3: Implement the fields, validator, and serializer** in `grammar/src/polymer_grammar/leaf.py`.

Add the two fields to `QuantityLeaf` (after `context`):

```python
    context: MeasurementContext | None = None
    low: float | None = None
    high: float | None = None
```

Extend the existing `_serialize` wrap-serializer to drop the new fields when None:

```python
    @model_serializer(mode="wrap")
    def _serialize(self, handler) -> dict:
        """Drop optional None-valued fields so a leaf without them serializes byte-identically to
        the pre-field grammar (no new key). Mirrors the additive-field pattern in capability.py."""
        data = handler(self)
        for key in ("context", "low", "high"):
            if data.get(key) is None:
                data.pop(key, None)
        return data
```

Add a second after-validator (below `_basis_discipline`):

```python
    @model_validator(mode="after")
    def _bound_discipline(self) -> "QuantityLeaf":
        lo, hi = self.low, self.high
        if lo is None and hi is None:
            return self
        if lo is not None and hi is not None and not lo < hi:
            raise ValueError(f"interval requires low < high; got low={lo}, high={hi}")
        if lo is not None and self.value < lo:
            raise ValueError(f"value {self.value} is below low bound {lo}")
        if hi is not None and self.value > hi:
            raise ValueError(f"value {self.value} is above high bound {hi}")
        if self.uncertainty is not None:
            raise ValueError(
                "uncertainty and explicit bounds are two spread encodings; set only one"
            )
        return self
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_leaf_bounds.py -v`
Expected: PASS (all).

- [ ] **Step 5: Regression — existing grammar suite green (byte-identity of 2a + all leaf tests)**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_leaf.py tests/test_leaf_context.py -q && uv run pytest -q`
Expected: PASS — in particular `test_leaf_context.py::test_context_less_leaf_is_byte_identical` still holds (the boundless baseline is unchanged by the new dropped fields). Report the full grammar count.

- [ ] **Step 6: Commit**

```bash
git add grammar/src/polymer_grammar/leaf.py grammar/tests/test_leaf_bounds.py
git commit -m "feat(grammar): optional low/high bounds on QuantityLeaf (GAP-3; byte-identical when boundless)"
```

---

### Task 2: Flip the armed C3 interval tripwire

**Files:**
- Modify: `src/polymer_claims/synbio/claims.py` (`car_threshold_claim`, lines ~88-109)
- Test: `tests/synbio/test_claims_intervals.py`

**Interfaces:**
- Consumes: `QuantityLeaf.low`/`high` (Task 1).

- [ ] **Step 1: Update the tripwire test** so it asserts the resolved shape (remove the `xfail`).

In `tests/synbio/test_claims_intervals.py`: (a) delete the `@pytest.mark.xfail(...)` decorator on `test_c3_interval_gap` so it must now pass; (b) in `test_c3_c4_build_as_derived`, add bounds assertions for C3 and keep the C4 point assertion:

```python
def test_c3_c4_build_as_derived():
    c3, c4 = car_threshold_claim(), endosomal_escape_claim()
    assert c3.leaves[0].value == 1e3
    assert c3.leaves[0].low == 1e2 and c3.leaves[0].high == 1e4   # NEW honest bounds
    assert c4.leaves[0].value == 0.03
    assert c3.leaves[0].measurement_basis is MeasurementBasis.DERIVED
    assert c4.leaves[0].measurement_basis is MeasurementBasis.DERIVED
    assert c3.leaves[0].uncertainty is None      # spread carried by bounds, not a fake bar


def test_c3_interval_gap():   # xfail decorator REMOVED — now must pass
    leaf = car_threshold_claim().leaves[0]
    assert getattr(leaf, "low", None) is not None and getattr(leaf, "high", None) is not None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/synbio/test_claims_intervals.py -v`
Expected: FAIL — C3 has no `low`/`high` yet (and the un-xfailed `test_c3_interval_gap` now fails).

- [ ] **Step 3: Re-express C3 with honest bounds** in `src/polymer_claims/synbio/claims.py` — keep `value=1e3` (within bounds), add `low=1e2, high=1e4`:

```python
        leaves=(
            QuantityLeaf(
                value=1e3,
                unit=None,
                uncertainty=None,
                measurement_basis=MeasurementBasis.DERIVED,
                formula="antigen_copies_at_half_max_activation",
                low=1e2,
                high=1e4,
            ),
        ),
```

Also update the docstring: drop the "GAP (interval): logged" line and note the bounds now carry the range.

- [ ] **Step 4: Run to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/synbio/test_claims_intervals.py -v`
Expected: PASS (both tests, no xfail).

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/synbio/claims.py tests/synbio/test_claims_intervals.py
git commit -m "feat(synbio): re-express C3 CAR threshold with honest low/high bounds; flip GAP-3 tripwire"
```

---

### Task 3: Extend the manifest pipeline to carry `low`/`high`

**Files:**
- Modify: `src/polymer_claims/synbio/manifest.py` (`ManifestLeaf`, lines ~28-41)
- Modify: `src/polymer_claims/synbio/ingest.py` (`build_claim`, the quantity branch)
- Test: `tests/synbio/test_ingest.py` (extend)

**Interfaces:**
- Consumes: `QuantityLeaf.low`/`high` (Task 1).
- Produces: `ManifestLeaf.low`/`high` (optional floats); `build_claim` threads them into the built `QuantityLeaf`.

- [ ] **Step 1: Write the failing test** — add to `tests/synbio/test_ingest.py`:

```python
def test_build_claim_threads_low_high_bounds():
    from polymer_claims.synbio.manifest import ManifestEntry
    from polymer_claims.synbio.ingest import build_claim
    from polymer_grammar.leaf import QuantityLeaf
    entry = ManifestEntry.model_validate({
        "id": "sb-test-range", "title": "t", "tier": 1, "topic": "computing",
        "leaf": {"kind": "quantity", "value": 10.0, "measurement_basis": "DERIVED",
                 "formula": "dynamic_range", "low": 10.0, "high": 100.0},
        "source": "PLM-VI", "schema_fit": {"status": "clean"},
    })
    leaf = build_claim(entry).leaves[0]
    assert isinstance(leaf, QuantityLeaf)
    assert leaf.low == 10.0 and leaf.high == 100.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/synbio/test_ingest.py::test_build_claim_threads_low_high_bounds -v`
Expected: FAIL — `ManifestLeaf` forbids the unknown `low`/`high` keys (`extra="forbid"`).

- [ ] **Step 3: Add the fields to `ManifestLeaf`** in `src/polymer_claims/synbio/manifest.py` (in the quantity block, after `formula`):

```python
    formula: str | None = None
    low: float | None = None
    high: float | None = None
    context: dict | None = None  # {tissue,cell_line,assay,condition}
```

- [ ] **Step 4: Thread them in `build_claim`** in `src/polymer_claims/synbio/ingest.py` (the `quantity` branch) — add `low`/`high` to the `QuantityLeaf(...)` call:

```python
        leaf: object = QuantityLeaf(
            value=leaf_spec.value,
            unit=leaf_spec.unit,
            uncertainty=leaf_spec.uncertainty,
            measurement_basis=MeasurementBasis[leaf_spec.measurement_basis],
            formula=leaf_spec.formula,
            context=_context(leaf_spec.context),
            low=leaf_spec.low,
            high=leaf_spec.high,
        )
```

- [ ] **Step 5: Run to verify it passes + no synbio regression**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/synbio/ -q`
Expected: PASS (all synbio; 1 xfail remains only if the deferred-marker tripwires from Task 4 are not yet added — at this point expect the pre-existing count with no new xfail).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/synbio/manifest.py src/polymer_claims/synbio/ingest.py tests/synbio/test_ingest.py
git commit -m "feat(synbio): carry low/high bounds through the manifest->claim pipeline"
```

---

### Task 4: Retire the five manifest gaps + mark GAP-5/6/9/10/12 resolved + arm deferred tripwires

**Files:**
- Modify: `data/synbio_compendia/manifests/plm-02-sensing.json`, `plm-03-sensing.json`, `plm-06-computing.json`, `plm-07-actuation.json`
- Modify: `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`
- Test: `tests/synbio/test_claims_intervals.py` (add two deferred-marker tripwires)
- Regenerate: `viewer/public/merged-universe.json`

**Interfaces:**
- Consumes: the manifest pipeline bounds (Task 3).

- [ ] **Step 1: Re-express the five interval-family entries.** For each, set `low`/`high`, set `value = low` (representative-value rule), drop the fabricated `uncertainty`, and flip `schema_fit` to `{"status": "clean"}`. Exact edits:

| file | entry id | set | schema_fit |
|---|---|---|---|
| plm-02-sensing.json | `sb-plm02-cd19-density-floor` | `low: 2000`, `value: 2000` (floor; `high` absent) | clean |
| plm-03-sensing.json | `sb-plm03-adar-leak-floor` | `low: 0.01`, `high: 0.03`, `value: 0.01`, remove `uncertainty` | clean |
| plm-06-computing.json | `sb-plm06-transcriptional-gate-dynamic-range` | `low: 10`, `high: 100`, `value: 10`, remove `uncertainty` | clean |
| plm-06-computing.json | `sb-plm06-cascade-depth-ceiling` | `low: 3`, `high: 4`, `value: 3`, remove `uncertainty` (keep `unit:"layers"`) | clean |
| plm-07-actuation.json | `sb-plm07-vivovec-bcell-depletion` | `low: 10`, `value: 10` (floor; `high` absent) | clean |

For each `schema_fit`, replace the whole object with `{"status": "clean"}` (drop the constraint/candidate/expansion_class/purity_cost keys).

- [ ] **Step 2: Add two deferred-marker tripwires** to `tests/synbio/test_claims_intervals.py` so the deferred refinements re-surface when a consumer appears:

```python
@pytest.mark.xfail(reason="GAP-9 deferred: no log/geometric-scale marker on QuantityLeaf (YAGNI, "
                          "no consumer computes inside the interval yet)", strict=True)
def test_gap9_logscale_marker_deferred():
    from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
    leaf = QuantityLeaf(value=10.0, measurement_basis=MeasurementBasis.DERIVED, formula="f",
                        low=10.0, high=100.0)
    assert getattr(leaf, "scale", None) == "log"


@pytest.mark.xfail(reason="GAP-10 deferred: no discrete-integer marker on QuantityLeaf (YAGNI, no "
                          "consumer interpolates inside the interval yet)", strict=True)
def test_gap10_discrete_marker_deferred():
    from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
    leaf = QuantityLeaf(value=3.0, unit="layers", measurement_basis=MeasurementBasis.FUNDAMENTAL,
                        low=3.0, high=4.0)
    assert getattr(leaf, "discrete", None) is True
```

- [ ] **Step 3: Verify the re-expressed manifests build and gaps drop** —

Run:
```bash
cd /Users/zbb2/Desktop/polymer-claims && uv run --project . python -c "
from pathlib import Path
from polymer_claims.synbio.manifest import load_manifest
from polymer_claims.synbio.ingest import build_manifest_claims
from polymer_claims.synbio.gap_ledger import aggregate_gaps
d = Path('data/synbio_compendia/manifests')
paths = sorted(d.glob('*.json'))
claims, _ = build_manifest_claims(paths)
entries = [e for p in paths for e in load_manifest(p)]
gaps = aggregate_gaps(entries)
print('claims build:', len(claims))
print('remaining gaps:', [g.constraint[:40] for g in gaps])
print('gap count:', len(gaps))
"
```
Expected: all claims build; gap count drops from 11 to 6 (the five interval-family gaps gone; GAP-7/8/11/13/14/15 remain). Then run `uv run --project . pytest tests/synbio/ -q` — expect PASS with the two new xfails (total 3 xfail: the two deferred markers + any pre-existing).

- [ ] **Step 4: Mark GAP-5/6/9/10/12 RESOLVED in the gap-log.** In `docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`, under each of the GAP-5, GAP-6, GAP-9, GAP-10, GAP-12 subsections, append a bold line:

```
- **RESOLVED (2026-07-12):** `QuantityLeaf.low`/`high` (additive, byte-identical) — the entry now carries honest bounds; `schema_fit` → clean. Deferred refinements (GAP-9 log-scale, GAP-10 discrete) tripwire-armed in `tests/synbio/test_claims_intervals.py`.
```

Update the "Harvest verdict" section: note that the interval/range/floor/bound family (5 of 11) is now retired by the GAP-3 slice; remaining open gaps are GAP-7 (analytic basis), GAP-8 (gene/locus context), GAP-11 (per-tumor stratification — its range facet is now expressible but its stratification residue keeps it open), GAP-13 (endpoint-type), GAP-14 (composite quantity), GAP-15 (structured categorical).

- [ ] **Step 5: Regenerate the merged universe** (SLOW ~13min — the real pharmaco scan runs):

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . python viewer/scripts/make_merged_universe.py 2>&1 | tail -8`
Expected: `by arm` shows `synthetic-biology: 44` and pharmaco/immuno/polymergenomics UNCHANGED; all synbio CONJECTURED. (The five re-expressed synbio nodes get new content — expected; other arms byte-stable.) Paste the output in the report.

- [ ] **Step 6: Commit**

```bash
git add data/synbio_compendia/manifests tests/synbio/test_claims_intervals.py docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md viewer/public/merged-universe.json
git commit -m "feat(synbio): retire GAP-5/6/9/10/12 — re-express 5 entries with low/high bounds; arm deferred markers"
```

---

### Task 5: Finalize — full gate + continuity

**Files:**
- Modify: `docs/superpowers/CONTINUE.md`
- Modify: memory (per protocol)

- [ ] **Step 1: Full gate.** Run the three suites + ruff:

```bash
cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -q
cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q
cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ -q       # SLOW ~13min
cd /Users/zbb2/Desktop/polymer-claims && uv run --project . ruff check grammar/src src/polymer_claims/synbio tests/synbio
```
Expected: grammar / protocol / umbrella all green (record counts); ruff clean on the touched files. (Pre-existing E702 in `src/polymer_claims/ingest/loyfer_wgbs.py` is out of scope — do not fix.)

- [ ] **Step 2: Update `CONTINUE.md`** — new session-close block: GAP-3 SHIPPED, `QuantityLeaf.low`/`high` added (additive, byte-identical), five gaps retired (GAP-5/6/9/10/12), gap-log now 6 open, deferred log/discrete markers tripwire-armed. Note grammar count delta and that the merged universe is unchanged in node count (44 synbio; five nodes re-expressed).

- [ ] **Step 3: Update memory** — append a LATEST block to `project_polymer_claims_knowledge_protocol.md` (GAP-3 shipped, the first core expansion since 2a, five gaps retired, the low/high recipe, deferred markers) and update the INDEX pointer. Link `[[feedback_ir_monotonic_expansion]]`.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/CONTINUE.md
git commit -m "docs(gap3): ship close — QuantityLeaf low/high, GAP-5/6/9/10/12 retired; CONTINUE + memory"
```

---

## Self-review (against the spec)

- **Fields + validators + serializer** → Task 1. ✔
- **Byte-identity + hash-stability** → Task 1 Steps 1/5 (boundless baseline unchanged; 2a byte-identity regression; DL slot-count stable). Merge-hash stability follows from serialization byte-identity (merge_universes hashes `claim.model_dump_json()`). ✔
- **Flip armed C3 tripwire** → Task 2. ✔
- **Manifest pipeline carries bounds** → Task 3 (ManifestLeaf + build_claim). ✔
- **Retire 5 gaps + mark resolved + arm deferred tripwires** → Task 4. ✔
- **Invariants** (pure/numpy-free, Corpus=4, additive+optional, CONJECTURED, basis discipline unchanged) → Global Constraints, enforced by Task 1 regression + Task 4 regen check. ✔
- **Scope: retire GAP-5/6/9/10/12; defer log/discrete markers with tripwires** → Task 4 Steps 1/2/4. GAP-11's range facet noted as now-expressible but kept open for its stratification residue. ✔
- **Type consistency:** `low`/`high: float | None` identical across `QuantityLeaf` (Task 1), `ManifestLeaf` (Task 3), and `build_claim` threading (Task 3). ✔
