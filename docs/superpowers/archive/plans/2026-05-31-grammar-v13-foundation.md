# Grammar v1.3 Foundation — Implementation Plan (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a cleanly-isolated `grammar/` package (`polymer_grammar`) and implement the foundational v1.3 claim-grammar primitives — the sum-typed L0 leaf, the status lifecycle, the 6-axis Pareto strength vector, the axis-derived pattern registry, and a claim skeleton wiring them together.

**Architecture:** A new top-level uv package `grammar/` sibling to the live v1.2 `formalclaim/`, with **zero imports across the boundary** — the current schema stays untouched and canonical; v1.3 grows in isolation. Pydantic v2 models, one focused module per primitive, TDD throughout.

**Tech Stack:** Python ≥3.12, pydantic v2, uv (package + runner), pytest, ruff. Mirrors the conventions already used in `formalclaim/`.

**Source spec:** `docs/superpowers/specs/2026-05-31-unified-claim-foundations-spec.md` (§3 the grammar). Schema reference: `docs/superpowers/specs/2026-05-31-claim-schema-overview.html`.

---

## Progress Log

**Status: Phase 1 COMPLETE + merged to `main` (merge commit `8f18666`, 2026-05-31). Tuple-immutability hardening done (this section's F1).**

Executed subagent-driven (fresh implementer + spec review + code-quality review per task; final whole-package review on Opus). All 7 tasks delivered; 29 tests at merge.

| Task | Status | Commit | Notes |
|---|---|---|---|
| 1 — Scaffold isolated package | ✅ | `01f217e` | uv pkg `polymer_grammar`, `_Model`, import test |
| 2 — Status + PendingReason enums | ✅ | `009a2d2` | 5 + 9 values |
| 3 — L0 sum-typed Leaf | ✅ | `236b147` → `a3670a3` | review drove **`frozen=True`** on `_Model` + parametrized non-fundamental unit-rejection test + docstring fix |
| 4 — StrengthVector (6-axis Pareto) | ✅ | `652bc1e` | meet/join/dominance/incomparability, `licensed` gate, no hidden scalar |
| 5 — Pattern registry | ✅ | `aff294a` | open axis-derived, seeded `adjusted_effect`; review flagged shallow-frozen lists (→ F1) |
| 6 — Claim skeleton | ✅ | `94181b8` | lifecycle invariants verified across all 6 status×reason cases |
| 7 — Isolation guard | ✅ | `7690ad5` | naive substring → anchored import regex (avoids docstring false-positive); 17 edge cases verified |

**Decisions made during execution:** (a) `_Model` is `frozen=True` (deviation from v1.2's mutable convention — justified: claims are immutable facts, prevents validator bypass, enables hashing). (b) Isolation guard uses an import-anchored regex, not substring.

### Follow-up F1 — tuple-immutability hardening ✅ (commit pending this section; branch `feat/grammar-tuple-immutability`)
The final review flagged that `frozen=True` is a *shallow* freeze: `list` fields stayed mutable in place and made `Claim`/`Pattern` unhashable (breaking the content-addressing rationale). Fixed: converted `Claim.leaves` and `Pattern.{intended_applications,excluded_applications,merged_from}` from `list[...]` → `tuple[...,...]` (pydantic coerces input lists automatically — no caller changes). Added `tests/test_immutability.py` (5 tests: tuple-coercion, in-place-mutation rejection, hashability of Claim + Pattern, equal-claims-hash-equal). Full suite now **34 passed**, ruff clean. `Claim`/`Pattern` are now genuinely deep-immutable and hashable for content-addressing.

### Remaining follow-ups (not yet done)
- Add `.pytest_cache/` + `.ruff_cache/` to root `.gitignore` (defensive; not tracked today).
- Document the extended `MeasurementBasis` (Conventional/Ordinal/Nominal beyond spec's Fundamental/Derived).
- `Pattern.adjustment_role` is a placeholder `str` → typed role slots (`predictor|outcome|confounder|...`) in a later phase.

### Next phases (each its own plan against the unified spec)
L1 molecular Proposition + asserted equivalence · licensing bridge ((σ,M) + dual route + `rival_set_closure`) · typed role slots + units-of-measure type system · L3 VAF defeat edges + Duhem blame-sets · L4 AGM/TMS revision · the 6 protocol-imposed fields · the evaluator.

---

## File Structure

New package, fully contained under `grammar/`:

```
grammar/
  pyproject.toml                       # uv package: polymer-grammar (isolated)
  README.md                            # one-paragraph: what this is, why separate from formalclaim
  src/polymer_grammar/
    __init__.py                        # public exports + __version__
    base.py                            # _Model base (extra="forbid")
    status.py                          # Status + PendingReason enums
    leaf.py                            # L0 sum-typed Leaf (Quantity|Categorical|Existence|Proposition)
    strength.py                        # StrengthVector (6-axis Pareto: meet/join/dominates/comparable)
    pattern.py                         # Pattern + PatternRef + in-memory registry (seeded adjusted_effect)
    claim.py                           # Claim skeleton wiring leaf+status+pattern+strength
  tests/
    test_status.py
    test_leaf.py
    test_strength.py
    test_pattern.py
    test_claim.py
```

Isolation rule (enforced in Task 7): nothing under `grammar/src/polymer_grammar/` may `import polymer_formalclaim`.

---

### Task 1: Scaffold the isolated `grammar/` package

**Files:**
- Create: `grammar/pyproject.toml`
- Create: `grammar/README.md`
- Create: `grammar/src/polymer_grammar/__init__.py`
- Create: `grammar/src/polymer_grammar/base.py`
- Test: `grammar/tests/test_status.py` (placeholder import test first)

- [ ] **Step 1: Create `grammar/pyproject.toml`**

```toml
[project]
name = "polymer-grammar"
version = "0.1.0"
description = "Polymer Claims v1.3 grammar — contained, kept apart from the v1.2 formalclaim IR."
requires-python = ">=3.12"
dependencies = ["pydantic>=2.6"]

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.6"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/polymer_grammar"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `grammar/README.md`**

```markdown
# polymer-grammar

The Polymer Claims **v1.3 grammar** — the next-generation claim IR derived from the
foundations spec (`docs/superpowers/specs/2026-05-31-unified-claim-foundations-spec.md`).

**This package is intentionally isolated from `formalclaim/` (the live v1.2 IR).** It does
not import from, and is not imported by, `polymer_formalclaim`. The v1.2 schema stays
canonical and untouched while v1.3 is built and validated here. A bridge/migration, if
ever needed, will be an explicit, separately-reviewed module — never an implicit import.
```

- [ ] **Step 3: Create `grammar/src/polymer_grammar/base.py`**

```python
"""Project base model for the v1.3 grammar."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    """Forbid extras so typos in fixtures fail loudly (mirrors formalclaim)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
```

- [ ] **Step 4: Create `grammar/src/polymer_grammar/__init__.py`**

```python
"""polymer_grammar — Polymer Claims v1.3 grammar (isolated from formalclaim)."""
from __future__ import annotations

__version__ = "0.1.0"

from .base import _Model

__all__ = ["_Model", "__version__"]
```

- [ ] **Step 5: Create `grammar/tests/test_status.py` with a placeholder import test**

```python
def test_package_imports():
    import polymer_grammar

    assert polymer_grammar.__version__ == "0.1.0"
```

- [ ] **Step 6: Run the test to verify the package is wired**

Run: `cd grammar && uv run pytest tests/test_status.py -v`
Expected: PASS (1 passed). If uv reports a missing interpreter, run `uv python install 3.12` first.

- [ ] **Step 7: Commit**

```bash
git add grammar/
git commit -m "feat(grammar): scaffold isolated polymer_grammar v1.3 package"
```

---

### Task 2: Status lifecycle + PENDING reason enums

**Files:**
- Create: `grammar/src/polymer_grammar/status.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_status.py`

- [ ] **Step 1: Replace `grammar/tests/test_status.py` with the failing tests**

```python
from polymer_grammar.status import PendingReason, Status


def test_package_imports():
    import polymer_grammar

    assert polymer_grammar.__version__ == "0.1.0"


def test_status_values():
    assert Status.LICENSED.value == "licensed"
    assert {s.value for s in Status} == {
        "conjectured",
        "exploratory",
        "pending",
        "licensed",
        "rejected",
    }


def test_pending_reasons_include_governance_and_incomparable():
    vals = {r.value for r in PendingReason}
    assert "unreproducible_by_governance" in vals
    assert "strength_incomparable" in vals
    assert "duhem_underdetermined" in vals
    assert len(vals) == 9
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd grammar && uv run pytest tests/test_status.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_grammar.status'`

- [ ] **Step 3: Create `grammar/src/polymer_grammar/status.py`**

```python
"""Claim status lifecycle and typed PENDING reason-codes (spec §3.5)."""
from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    CONJECTURED = "conjectured"
    EXPLORATORY = "exploratory"
    PENDING = "pending"
    LICENSED = "licensed"
    REJECTED = "rejected"


class PendingReason(str, Enum):
    UNTESTED = "untested"
    UNDERPOWERED = "underpowered"
    EXPLORATORY_BY_DESIGN = "exploratory_by_design"
    CONTESTED = "contested"
    DUHEM_UNDERDETERMINED = "duhem_underdetermined"
    DEFINITIONAL_COMMITMENT_CONTESTED = "definitional_commitment_contested"
    ONTOLOGY_TERM_OBSOLETE = "ontology_term_obsolete"
    STRENGTH_INCOMPARABLE = "strength_incomparable"
    UNREPRODUCIBLE_BY_GOVERNANCE = "unreproducible_by_governance"
```

- [ ] **Step 4: Export from `grammar/src/polymer_grammar/__init__.py`**

```python
"""polymer_grammar — Polymer Claims v1.3 grammar (isolated from formalclaim)."""
from __future__ import annotations

__version__ = "0.1.0"

from .base import _Model
from .status import PendingReason, Status

__all__ = ["_Model", "PendingReason", "Status", "__version__"]
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd grammar && uv run pytest tests/test_status.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add grammar/
git commit -m "feat(grammar): status lifecycle + typed PENDING reason-codes"
```

---

### Task 3: L0 sum-typed Leaf (the highest-leverage primitive)

**Files:**
- Create: `grammar/src/polymer_grammar/leaf.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_leaf.py`

- [ ] **Step 1: Write the failing tests `grammar/tests/test_leaf.py`**

```python
import pytest
from pydantic import TypeAdapter, ValidationError

from polymer_grammar.leaf import (
    CategoricalLeaf,
    ExistenceLeaf,
    Leaf,
    MeasurementBasis,
    PropositionLeaf,
    QuantityLeaf,
)

ADAPTER = TypeAdapter(Leaf)


def test_quantity_fundamental_may_carry_unit():
    leaf = QuantityLeaf(
        value=37.0, unit="Cel", uncertainty=0.5,
        measurement_basis=MeasurementBasis.FUNDAMENTAL,
    )
    assert leaf.kind == "quantity"
    assert leaf.unit == "Cel"


def test_quantity_derived_requires_formula_and_forbids_unit():
    # derived statistic (e.g. partial-rho) must carry its generating formula, not a unit
    leaf = QuantityLeaf(
        value=-0.238, measurement_basis=MeasurementBasis.DERIVED,
        formula="ppcor::pcor.test(curvature, co_rate | gc)",
    )
    assert leaf.formula is not None
    with pytest.raises(ValidationError):
        QuantityLeaf(value=-0.238, unit="ratio", measurement_basis=MeasurementBasis.DERIVED,
                     formula="x")  # unit forbidden on derived


def test_quantity_derived_without_formula_rejected():
    with pytest.raises(ValidationError):
        QuantityLeaf(value=-0.18, measurement_basis=MeasurementBasis.DERIVED)


def test_categorical_carries_ontology_term_not_unit():
    leaf = CategoricalLeaf(ontology_term="SO:0000657", assay="ChromHMM")
    assert leaf.kind == "categorical"


def test_existence_distinguishes_absence_from_untested():
    leaf = ExistenceLeaf(state="not_detected", detection_limit=0.01)
    assert leaf.kind == "existence"


def test_proposition_leaf_is_a_toulmin_warrant():
    leaf = PropositionLeaf(
        data="cross-cell-type methylation variance is class-specific",
        warrant="KZFP/TRIM28 silencing targets young LTRs",
        warrant_type="mechanistic_analogy",
    )
    assert leaf.kind == "proposition"


def test_discriminated_union_dispatches_on_kind():
    leaf = ADAPTER.validate_python(
        {"kind": "existence", "state": "observed"}
    )
    assert isinstance(leaf, ExistenceLeaf)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd grammar && uv run pytest tests/test_leaf.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_grammar.leaf'`

- [ ] **Step 3: Create `grammar/src/polymer_grammar/leaf.py`**

```python
"""L0 — the sum-typed empirical anchor (spec §3.3).

Only a Fundamental quantity (one backed by a representation theorem) may assert a
UCUM unit + meaningfulness class. Derived statistics carry their generating formula,
never a false unit. Categorical leaves carry an ontology term instead of a unit;
Existence leaves distinguish genuine absence from untested absence; Proposition
leaves give qualitative/mechanistic claims a Toulmin-warrant home.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from .base import _Model


class MeasurementBasis(str, Enum):
    FUNDAMENTAL = "fundamental"
    DERIVED = "derived"
    CONVENTIONAL = "conventional"
    ORDINAL = "ordinal"
    NOMINAL = "nominal"


class QuantityLeaf(_Model):
    kind: Literal["quantity"] = "quantity"
    value: float
    unit: str | None = None
    uncertainty: float | None = None
    measurement_basis: MeasurementBasis
    formula: str | None = None

    @model_validator(mode="after")
    def _basis_discipline(self) -> "QuantityLeaf":
        if self.measurement_basis == MeasurementBasis.FUNDAMENTAL:
            return self
        # Non-fundamental: a UCUM unit is meaningless; require the generating formula
        # for DERIVED quantities and forbid a unit on anything non-fundamental.
        if self.unit is not None:
            raise ValueError(
                f"unit is only meaningful for FUNDAMENTAL quantities; "
                f"got unit={self.unit!r} with basis={self.measurement_basis.value}"
            )
        if self.measurement_basis == MeasurementBasis.DERIVED and not self.formula:
            raise ValueError("DERIVED quantity must carry its generating `formula`")
        return self


class CategoricalLeaf(_Model):
    kind: Literal["categorical"] = "categorical"
    ontology_term: str
    assay: str | None = None


class ExistenceLeaf(_Model):
    kind: Literal["existence"] = "existence"
    state: Literal["observed", "not_detected"]
    detection_limit: float | None = None


class PropositionLeaf(_Model):
    kind: Literal["proposition"] = "proposition"
    data: str
    warrant: str
    backing: str | None = None
    qualifier: str | None = None
    rebuttal: str | None = None
    warrant_type: Literal[
        "deductive",
        "mechanistic_analogy",
        "assay_incommensurability",
        "expert_judgment",
    ] = "mechanistic_analogy"


Leaf = Annotated[
    Union[QuantityLeaf, CategoricalLeaf, ExistenceLeaf, PropositionLeaf],
    Field(discriminator="kind"),
]
```

- [ ] **Step 4: Export from `__init__.py`**

```python
"""polymer_grammar — Polymer Claims v1.3 grammar (isolated from formalclaim)."""
from __future__ import annotations

__version__ = "0.1.0"

from .base import _Model
from .leaf import (
    CategoricalLeaf,
    ExistenceLeaf,
    Leaf,
    MeasurementBasis,
    PropositionLeaf,
    QuantityLeaf,
)
from .status import PendingReason, Status

__all__ = [
    "_Model",
    "CategoricalLeaf",
    "ExistenceLeaf",
    "Leaf",
    "MeasurementBasis",
    "PendingReason",
    "PropositionLeaf",
    "QuantityLeaf",
    "Status",
    "__version__",
]
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd grammar && uv run pytest tests/test_leaf.py -v`
Expected: PASS (7 passed)

- [ ] **Step 6: Commit**

```bash
git add grammar/
git commit -m "feat(grammar): L0 sum-typed leaf (Quantity/Categorical/Existence/Proposition)"
```

---

### Task 4: StrengthVector — 6-axis Pareto partial order

**Files:**
- Create: `grammar/src/polymer_grammar/strength.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_strength.py`

- [ ] **Step 1: Write the failing tests `grammar/tests/test_strength.py`**

```python
from polymer_grammar.strength import AXES, StrengthVector, licensed


def _v(**kw):
    base = dict(
        magnitude=0.5, uncertainty=0.5, evidence_against_null=0.5,
        severity=0.5, world_contact=0.5, explanatory_virtue=0.5,
    )
    base.update(kw)
    return StrengthVector(**base)


def test_axes_are_the_six():
    assert AXES == (
        "magnitude", "uncertainty", "evidence_against_null",
        "severity", "world_contact", "explanatory_virtue",
    )


def test_meet_is_componentwise_min():  # AND = weakest link
    a = _v(magnitude=0.9, severity=0.2)
    b = _v(magnitude=0.3, severity=0.8)
    m = a.meet(b)
    assert m.magnitude == 0.3
    assert m.severity == 0.2


def test_join_is_componentwise_max():  # OR
    a = _v(magnitude=0.9, severity=0.2)
    b = _v(magnitude=0.3, severity=0.8)
    j = a.join(b)
    assert j.magnitude == 0.9
    assert j.severity == 0.8


def test_dominance_and_incomparability():
    strong = _v(magnitude=0.9, severity=0.9)
    weak = _v(magnitude=0.4, severity=0.4)
    assert strong.dominates(weak)
    assert not weak.dominates(strong)
    assert strong.comparable(weak)

    # trade-off → genuinely incomparable
    a = _v(magnitude=0.9, severity=0.2)
    b = _v(magnitude=0.2, severity=0.9)
    assert not a.dominates(b)
    assert not b.dominates(a)
    assert not a.comparable(b)


def test_licensed_requires_dominating_threshold_on_every_axis():
    threshold = _v(**{ax: 0.6 for ax in AXES})
    passing = _v(**{ax: 0.7 for ax in AXES})
    one_short = passing.model_copy(update={"severity": 0.5})
    assert licensed(passing, threshold)
    assert not licensed(one_short, threshold)  # fails on the single low axis
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd grammar && uv run pytest tests/test_strength.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_grammar.strength'`

- [ ] **Step 3: Create `grammar/src/polymer_grammar/strength.py`**

```python
"""Strength as a 6-axis Pareto partial order (spec §3.5).

AND = componentwise meet (weakest link); OR = componentwise join. Two claims with a
cross-axis trade-off are genuinely *incomparable* — there is no hidden scalar and no
Arrow-style aggregation. A claim is LICENSED only if it dominates a declared threshold
vector on EVERY axis.
"""
from __future__ import annotations

from pydantic import Field

from .base import _Model

AXES: tuple[str, ...] = (
    "magnitude",
    "uncertainty",
    "evidence_against_null",
    "severity",
    "world_contact",
    "explanatory_virtue",
)


class StrengthVector(_Model):
    magnitude: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    evidence_against_null: float = Field(ge=0.0, le=1.0)
    severity: float = Field(ge=0.0, le=1.0)
    world_contact: float = Field(ge=0.0, le=1.0)
    explanatory_virtue: float = Field(ge=0.0, le=1.0)

    def _vals(self) -> tuple[float, ...]:
        return tuple(getattr(self, ax) for ax in AXES)

    def meet(self, other: "StrengthVector") -> "StrengthVector":
        return StrengthVector(**{ax: min(getattr(self, ax), getattr(other, ax)) for ax in AXES})

    def join(self, other: "StrengthVector") -> "StrengthVector":
        return StrengthVector(**{ax: max(getattr(self, ax), getattr(other, ax)) for ax in AXES})

    def dominates(self, other: "StrengthVector") -> bool:
        return all(getattr(self, ax) >= getattr(other, ax) for ax in AXES)

    def comparable(self, other: "StrengthVector") -> bool:
        return self.dominates(other) or other.dominates(self)


def licensed(candidate: StrengthVector, threshold: StrengthVector) -> bool:
    """LICENSED ⇔ candidate dominates the threshold on every axis (conjunctive gate)."""
    return candidate.dominates(threshold)
```

- [ ] **Step 4: Export from `__init__.py`** (append the strength imports + names)

```python
from .strength import AXES, StrengthVector, licensed
```
Add `"AXES"`, `"StrengthVector"`, `"licensed"` to `__all__`.

- [ ] **Step 5: Run to verify it passes**

Run: `cd grammar && uv run pytest tests/test_strength.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add grammar/
git commit -m "feat(grammar): 6-axis Pareto StrengthVector (meet/join/dominance + licensed gate)"
```

---

### Task 5: Pattern object + axis-derived registry

**Files:**
- Create: `grammar/src/polymer_grammar/pattern.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_pattern.py`

- [ ] **Step 1: Write the failing tests `grammar/tests/test_pattern.py`**

```python
import pytest
from pydantic import ValidationError

from polymer_grammar.pattern import Pattern, PatternRef, get_pattern, registry


def test_adjusted_effect_is_seeded_and_merges_two_legacy_patterns():
    p = get_pattern("adjusted_effect", "v1")
    assert p.estimand == "adjusted_effect_size"
    # the merge note: partial_correlation_with_control + model_delta_over_baseline
    assert "partial_correlation_with_control" in p.merged_from
    assert "model_delta_over_baseline" in p.merged_from


def test_pattern_requires_at_least_one_excluded_application():
    with pytest.raises(ValidationError):
        Pattern(
            id="bad", version="v1", estimand="x", null_model="permutation",
            scale="ratio", invariance_group="affine",
            intended_applications=["something"], excluded_applications=[],
        )


def test_registry_lookup_misses_raise():
    with pytest.raises(KeyError):
        get_pattern("does_not_exist", "v1")


def test_pattern_ref_round_trips():
    ref = PatternRef(id="adjusted_effect", version="v1")
    assert get_pattern(ref.id, ref.version).id == "adjusted_effect"


def test_coverage_metric_reports_registry_size_not_closure():
    assert registry.coverage()["n_patterns"] >= 1
    assert registry.coverage()["closed"] is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd grammar && uv run pytest tests/test_pattern.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_grammar.pattern'`

- [ ] **Step 3: Create `grammar/src/polymer_grammar/pattern.py`**

```python
"""Pattern registry — an open, axis-derived catalog (spec §3.1).

A pattern is a typed signature over the statistical-form axes (estimand × adjustment
role × null model × scale) plus its invariance group and at least one *excluded*
application (which pins the relation, closing the Newman hole). The registry is OPEN:
it reports a coverage metric, never closure. `adjusted_effect` merges the legacy
`partial_correlation_with_control` and `model_delta_over_baseline` patterns.
"""
from __future__ import annotations

from pydantic import field_validator

from .base import _Model


class PatternRef(_Model):
    id: str
    version: str


class Pattern(_Model):
    id: str
    version: str
    estimand: str
    adjustment_role: str | None = None
    null_model: str
    scale: str
    invariance_group: str
    intended_applications: list[str]
    excluded_applications: list[str]
    merged_from: list[str] = []

    @field_validator("excluded_applications")
    @classmethod
    def _at_least_one_exclusion(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError(
                "a pattern must declare >=1 excluded_application to pin its relation"
            )
        return v


class _Registry:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], Pattern] = {}

    def register(self, pattern: Pattern) -> None:
        self._by_key[(pattern.id, pattern.version)] = pattern

    def get(self, id: str, version: str) -> Pattern:
        return self._by_key[(id, version)]

    def coverage(self) -> dict:
        return {"n_patterns": len(self._by_key), "closed": False}


registry = _Registry()

registry.register(
    Pattern(
        id="adjusted_effect",
        version="v1",
        estimand="adjusted_effect_size",
        adjustment_role="confounder_set",
        null_model="permutation_or_analytic",
        scale="standardized",
        invariance_group="monotone_reparametrization",
        intended_applications=[
            "partial correlation of a predictor with an outcome controlling for confounders",
            "model performance delta over a baseline after adjustment",
        ],
        excluded_applications=[
            "unadjusted bivariate correlation (use simple_correlation)",
            "causal-edge assertion (use the mechanism/causal pattern)",
        ],
        merged_from=["partial_correlation_with_control", "model_delta_over_baseline"],
    )
)


def get_pattern(id: str, version: str) -> Pattern:
    return registry.get(id, version)
```

- [ ] **Step 4: Export from `__init__.py`**

```python
from .pattern import Pattern, PatternRef, get_pattern, registry
```
Add `"Pattern"`, `"PatternRef"`, `"get_pattern"`, `"registry"` to `__all__`.

- [ ] **Step 5: Run to verify it passes**

Run: `cd grammar && uv run pytest tests/test_pattern.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add grammar/
git commit -m "feat(grammar): open axis-derived pattern registry (seeded adjusted_effect)"
```

---

### Task 6: Claim skeleton wiring the primitives together

**Files:**
- Create: `grammar/src/polymer_grammar/claim.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_claim.py`

- [ ] **Step 1: Write the failing tests `grammar/tests/test_claim.py`**

```python
import pytest
from pydantic import ValidationError

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import PendingReason, Status
from polymer_grammar.strength import StrengthVector


def _leaf():
    return QuantityLeaf(
        value=-0.238, measurement_basis=MeasurementBasis.DERIVED,
        formula="ppcor::pcor.test(curvature, co_rate | gc)",
    )


def _strength(**kw):
    base = dict(
        magnitude=0.7, uncertainty=0.7, evidence_against_null=0.7,
        severity=0.7, world_contact=0.7, explanatory_virtue=0.7,
    )
    base.update(kw)
    return StrengthVector(**base)


def test_minimal_licensed_claim_builds():
    claim = Claim(
        id="recomb_curvature_co",
        title="Curvature disfavors crossover after GC control",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=[_leaf()],
        status=Status.LICENSED,
        strength=_strength(),
    )
    assert claim.schema_version == "v1.3"
    assert claim.pattern.id == "adjusted_effect"


def test_pending_status_requires_a_reason():
    with pytest.raises(ValidationError):
        Claim(
            id="x", title="t",
            pattern=PatternRef(id="adjusted_effect", version="v1"),
            leaves=[_leaf()], status=Status.PENDING,  # no pending_reason
        )


def test_pending_with_reason_is_valid():
    claim = Claim(
        id="x", title="t",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=[_leaf()], status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
    )
    assert claim.pending_reason == PendingReason.UNTESTED


def test_pending_reason_only_allowed_when_pending():
    with pytest.raises(ValidationError):
        Claim(
            id="x", title="t",
            pattern=PatternRef(id="adjusted_effect", version="v1"),
            leaves=[_leaf()], status=Status.LICENSED,
            pending_reason=PendingReason.UNTESTED,  # contradicts LICENSED
        )


def test_claim_requires_at_least_one_leaf():
    with pytest.raises(ValidationError):
        Claim(
            id="x", title="t",
            pattern=PatternRef(id="adjusted_effect", version="v1"),
            leaves=[], status=Status.CONJECTURED,
        )
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd grammar && uv run pytest tests/test_claim.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_grammar.claim'`

- [ ] **Step 3: Create `grammar/src/polymer_grammar/claim.py`**

```python
"""The v1.3 Claim skeleton (spec §3, "The claim object").

Phase 1 wires the foundational primitives: a pattern reference, ≥1 L0 leaf, a status
with its lifecycle invariants, and an optional Pareto strength vector. Later phases add
the L1 molecular Proposition, the licensing bridge, L3 defeat edges, L4 revision, and
the protocol-imposed provenance fields.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import _Model
from .leaf import Leaf
from .pattern import PatternRef
from .status import PendingReason, Status
from .strength import StrengthVector


class Claim(_Model):
    schema_version: Literal["v1.3"] = "v1.3"
    id: str
    title: str
    pattern: PatternRef
    leaves: list[Leaf] = Field(min_length=1)
    status: Status
    pending_reason: PendingReason | None = None
    strength: StrengthVector | None = None

    @model_validator(mode="after")
    def _pending_reason_iff_pending(self) -> "Claim":
        if self.status == Status.PENDING and self.pending_reason is None:
            raise ValueError("status=PENDING requires a `pending_reason`")
        if self.status != Status.PENDING and self.pending_reason is not None:
            raise ValueError(
                f"`pending_reason` is only valid when status=PENDING; "
                f"got status={self.status.value}"
            )
        return self
```

- [ ] **Step 4: Export from `__init__.py`**

```python
from .claim import Claim
```
Add `"Claim"` to `__all__`.

- [ ] **Step 5: Run to verify it passes**

Run: `cd grammar && uv run pytest tests/test_claim.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Run the whole suite**

Run: `cd grammar && uv run pytest -v`
Expected: PASS (all tests across the 5 test files; 25 total)

- [ ] **Step 7: Commit**

```bash
git add grammar/
git commit -m "feat(grammar): Claim skeleton wiring leaf/status/pattern/strength with lifecycle invariants"
```

---

### Task 7: Isolation guard — assert no cross-import with formalclaim

**Files:**
- Create: `grammar/tests/test_isolation.py`

- [ ] **Step 1: Write the failing/guard test `grammar/tests/test_isolation.py`**

```python
"""Guard the containment boundary: polymer_grammar must not depend on the v1.2 IR."""
from __future__ import annotations

import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "polymer_grammar"


def test_no_import_of_formalclaim_anywhere_in_package():
    offenders = []
    for py in SRC.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if "polymer_formalclaim" in text or "from formalclaim" in text:
            offenders.append(py.name)
    assert offenders == [], f"v1.3 grammar must stay isolated; offenders: {offenders}"
```

- [ ] **Step 2: Run to verify it passes (no offenders expected)**

Run: `cd grammar && uv run pytest tests/test_isolation.py -v`
Expected: PASS (1 passed)

- [ ] **Step 3: Run the full suite + ruff**

Run: `cd grammar && uv run pytest -v && uv run ruff check src tests`
Expected: all tests PASS; ruff reports no errors (fix any it flags).

- [ ] **Step 4: Commit**

```bash
git add grammar/
git commit -m "test(grammar): isolation guard — no cross-import with formalclaim v1.2"
```

---

## Self-Review

**Spec coverage (§3 grammar primitives, Phase 1 subset):**
- §3.3 sum-typed L0 leaf → Task 3 ✓ (incl. the Fundamental-only-unit / Derived-needs-formula discipline)
- §3.5 status lifecycle + typed PENDING enum → Task 2 ✓; lifecycle invariant → Task 6 ✓
- §3.5 6-axis Pareto strength + incomparability + conjunctive licensed gate → Task 4 ✓
- §3.1 axis-derived open pattern registry + merged `adjusted_effect` + ≥1 excluded application → Task 5 ✓
- claim object skeleton → Task 6 ✓
- Containment constraint (kept apart from formalclaim) → Task 1 (separate package) + Task 7 (enforced guard) ✓

**Deferred to later Phase plans (explicitly out of scope here):** L1 molecular Proposition + asserted equivalence; the licensing bridge (`(σ,M)`, dual route, `rival_set_closure`); typed role slots + units-of-measure type system; L3 VAF defeat edges + Duhem blame sets; L4 AGM/TMS; the 6 protocol-imposed fields; the evaluator/materialization. Each is a separate plan against the same spec.

**Placeholder scan:** no TBD/TODO; every code step contains complete code; every run step has an exact command + expected outcome.

**Type consistency:** `StrengthVector` axis names match across Task 4 and the spec; `PatternRef`/`Pattern` names consistent Task 5↔6; `Status`/`PendingReason` consistent Task 2↔6; `Leaf` union + `MeasurementBasis` consistent Task 3↔6.
