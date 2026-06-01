# Typed Causal Roles + Units-of-Measure Algebra — Implementation Plan (Phase 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task-by-task. Steps use checkbox (`- [ ]`).

**Goal:** Add typed causal role slots (with a *derived* adjustment set that forecloses the Table-2 fallacy) and a `Dimension` abelian-group units algebra (with an optional `dimension` on the quantity leaf).

**Architecture:** Additive to the isolated `grammar/` package (frozen pydantic v2 models; tuple fields for hashability). Two independent modules (`roles.py`, `units.py`); one optional field on `Claim`, one on `QuantityLeaf`. TDD throughout.

**Tech Stack:** Python ≥3.12, pydantic v2, uv, pytest, ruff.

**Source spec:** `docs/superpowers/specs/2026-06-01-L2b-roles-and-units-spec.md`. Builds on Phases 1–3 (68 tests).

---

## Progress Log

_(Append a dated entry per completed task: commit SHA + outcome. Update after every task.)_

- 2026-06-01 — Task 1 ✅ causal roles, commit 55afdff, 6 tests (74 total).
- 2026-06-01 — Task 2 ✅ Claim.roles wired, commit 1ff4106, 3 tests (77 total).
- 2026-06-01 — Task 3 ✅ Dimension algebra, commit 9be1186, 7 tests (84 total).

---

## File Structure

```
grammar/src/polymer_grammar/
  roles.py   # NEW: Role, CausalRoles (+ adjustment_set)
  units.py   # NEW: Dimension (+ DIMENSIONLESS, ops), compatible
  claim.py   # MODIFY: add roles: CausalRoles | None = None
  leaf.py    # MODIFY: add dimension: Dimension | None = None to QuantityLeaf
  __init__.py
grammar/tests/
  test_roles.py / test_units.py / test_claim_roles.py / test_leaf_dimension.py
```

---

### Task 1: `roles.py` — typed causal roles + derived adjustment set

**Files:** Create `grammar/src/polymer_grammar/roles.py`; Modify `__init__.py`; Test `grammar/tests/test_roles.py`

- [ ] **Step 1: Write failing tests `grammar/tests/test_roles.py`**

```python
import pytest
from pydantic import ValidationError

from polymer_grammar.roles import CausalRoles, Role


def test_role_values():
    assert {r.value for r in Role} == {
        "predictor", "outcome", "confounder", "mediator", "collider", "instrument",
    }


def test_causal_roles_builds_and_derives_adjustment_set():
    r = CausalRoles(predictor="curvature", outcome="crossover_rate",
                    confounders=("gc_content",))
    assert r.adjustment_set == frozenset({"gc_content"})


def test_predictor_outcome_must_differ():
    with pytest.raises(ValidationError):
        CausalRoles(predictor="x", outcome="x")


def test_a_variable_cannot_hold_two_roles():
    with pytest.raises(ValidationError):
        CausalRoles(predictor="x", outcome="y",
                    confounders=("z",), mediators=("z",))


def test_adjustment_set_excludes_mediators_colliders_instruments():
    r = CausalRoles(predictor="x", outcome="y", confounders=("c",),
                    mediators=("m",), colliders=("k",), instruments=("i",))
    assert r.adjustment_set == frozenset({"c"})
    assert r.adjustment_set.isdisjoint({"m", "k", "i"})


def test_causal_roles_is_hashable():
    assert isinstance(hash(CausalRoles(predictor="x", outcome="y")), int)
```

- [ ] **Step 2: Run to verify FAIL**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_roles.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'polymer_grammar.roles'`)

- [ ] **Step 3: Create `grammar/src/polymer_grammar/roles.py`**

```python
"""Typed causal role slots (spec §1; unified spec §3.1).

A claim's variables are tagged with their causal role. The adjustment set is DERIVED
from the roles (= the confounders), never authored: you adjust for confounders, never
for mediators (blocks the effect — the Table-2 fallacy) or colliders (opens a spurious
path). Pearl's causal-hierarchy discipline in minimal form. Roles bind plain variable
names; ontology-backed subjects are a separate later concern.
"""
from __future__ import annotations

from enum import Enum

from pydantic import model_validator

from .base import _Model


class Role(str, Enum):
    PREDICTOR = "predictor"
    OUTCOME = "outcome"
    CONFOUNDER = "confounder"
    MEDIATOR = "mediator"
    COLLIDER = "collider"
    INSTRUMENT = "instrument"


class CausalRoles(_Model):
    predictor: str
    outcome: str
    confounders: tuple[str, ...] = ()
    mediators: tuple[str, ...] = ()
    colliders: tuple[str, ...] = ()
    instruments: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _predictor_outcome_distinct(self) -> "CausalRoles":
        if self.predictor == self.outcome:
            raise ValueError("predictor and outcome must be distinct variables")
        return self

    @model_validator(mode="after")
    def _each_variable_has_one_role(self) -> "CausalRoles":
        assignments = [self.predictor, self.outcome, *self.confounders,
                       *self.mediators, *self.colliders, *self.instruments]
        seen: set[str] = set()
        dupes: set[str] = set()
        for v in assignments:
            if v in seen:
                dupes.add(v)
            seen.add(v)
        if dupes:
            raise ValueError(
                f"each variable may hold at most one causal role; "
                f"multiply-assigned: {sorted(dupes)}"
            )
        return self

    @property
    def adjustment_set(self) -> frozenset[str]:
        """Derived minimal sufficient adjustment set = the confounders. Mediators,
        colliders, and instruments are excluded by construction (no authoring path)."""
        return frozenset(self.confounders)
```

- [ ] **Step 4: Export from `__init__.py`** — add `from .roles import CausalRoles, Role`; add `"CausalRoles"`, `"Role"` to `__all__`.

- [ ] **Step 5: Run to verify PASS**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_roles.py -v` → expect 6 passed. Then `uv run pytest -q` → expect 74 (68 + 6).

- [ ] **Step 6: Commit + Progress Log**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/
git commit -m "feat(grammar): typed causal roles + derived adjustment set (Table-2 guard)"
```
Append `- 2026-06-01 — Task 1 ✅ causal roles, commit <SHA>, 6 tests (74 total).` then commit the doc with `docs(plan): Phase 4 progress — Task 1 complete`.

---

### Task 2: wire `Claim.roles` (additive)

**Files:** Modify `claim.py`; Test `grammar/tests/test_claim_roles.py`

- [ ] **Step 1: Write failing tests `grammar/tests/test_claim_roles.py`**

```python
from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.roles import CausalRoles
from polymer_grammar.status import Status


def _leaf():
    return QuantityLeaf(value=-0.238, measurement_basis=MeasurementBasis.DERIVED,
                        formula="ppcor::pcor.test(curvature, co_rate | gc)")


def _claim(**kw):
    base = dict(id="c", title="t",
                pattern=PatternRef(id="adjusted_effect", version="v1"),
                leaves=[_leaf()], status=Status.CONJECTURED)
    base.update(kw)
    return Claim(**base)


def test_claim_without_roles_still_builds():  # back-compat
    assert _claim().roles is None


def test_claim_with_roles_builds_and_exposes_adjustment_set():
    roles = CausalRoles(predictor="curvature", outcome="crossover_rate",
                        confounders=("gc_content",))
    c = _claim(roles=roles)
    assert c.roles.adjustment_set == frozenset({"gc_content"})


def test_claim_with_roles_is_hashable():
    roles = CausalRoles(predictor="x", outcome="y")
    assert isinstance(hash(_claim(roles=roles)), int)
```

- [ ] **Step 2: Run to verify FAIL** — `uv run pytest tests/test_claim_roles.py -v` → FAIL (extra="forbid" rejects `roles`).

- [ ] **Step 3: Modify `grammar/src/polymer_grammar/claim.py`**
- Add import with the other `.` imports: `from .roles import CausalRoles`
- Add field after `licensing`:
```python
    roles: CausalRoles | None = None
```
No validator needed (roles self-validate; no cross-field constraint). Leave all else unchanged.

- [ ] **Step 4: Run to verify PASS** — `uv run pytest -v` → full suite **77** (74 + 3), prior unaffected.

- [ ] **Step 5: Commit + Progress Log** — `feat(grammar): wire optional Claim.roles (additive)`; append `- Task 2 ✅ Claim.roles wired, commit <SHA>, 3 tests (77 total).`

---

### Task 3: `units.py` — `Dimension` abelian-group algebra

**Files:** Create `grammar/src/polymer_grammar/units.py`; Modify `__init__.py`; Test `grammar/tests/test_units.py`

- [ ] **Step 1: Write failing tests `grammar/tests/test_units.py`**

```python
from polymer_grammar.units import DIMENSIONLESS, Dimension, compatible

L = Dimension.base("length")
T = Dimension.base("time")
M = Dimension.base("mass")


def test_base_and_dimensionless():
    assert L.exponents == (("length", 1),)
    assert DIMENSIONLESS.is_dimensionless
    assert not L.is_dimensionless


def test_multiplication_adds_exponents():
    area = L * L
    assert area.exponents == (("length", 2),)


def test_division_subtracts_exponents():
    velocity = L / T
    assert velocity == Dimension(exponents=(("length", 1), ("time", -1)))


def test_identity_inverse_associative_commutative():
    assert L * DIMENSIONLESS == L                       # identity
    assert L * (L ** -1) == DIMENSIONLESS               # inverse
    assert (L * T) * M == L * (T * M)                   # associative
    assert L * T == T * L                               # commutative


def test_normalization_drops_zero_and_is_canonical():
    # redundant opposite exponents cancel; explicit zero dropped; order canonical
    assert Dimension(exponents=(("length", 1), ("length", -1))).is_dimensionless
    assert Dimension(exponents=(("a", 0), ("b", 2))) == Dimension(exponents=(("b", 2),))
    assert Dimension(exponents=(("time", -1), ("length", 1))) == L / T  # order-independent


def test_compatible_is_equality():
    assert compatible(L / T, L / T)
    assert not compatible(L, T)


def test_dimension_is_hashable():
    assert isinstance(hash(L / T), int)
    assert len({L, L, T}) == 2
```

- [ ] **Step 2: Run to verify FAIL** — `uv run pytest tests/test_units.py -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Create `grammar/src/polymer_grammar/units.py`**

```python
"""Units-of-measure algebra (spec §2; unified spec §3.1).

Dimension as an abelian group over base dimensions (base -> integer exponent;
multiply = add exponents). Makes dimensional reasoning decidable (Kennedy 1997;
Buckingham Π for free). The canonical representation is a sorted tuple of
(base, exponent) pairs with no zero exponents — so the model is frozen, hashable,
and equality is structural. DIMENSIONLESS is the group identity. Enforcement against
quantity arithmetic is the evaluator phase; this module ships the type.
"""
from __future__ import annotations

from pydantic import field_validator

from .base import _Model


class Dimension(_Model):
    # canonical: sorted tuple of (base, exponent) pairs, no zero exponents
    exponents: tuple[tuple[str, int], ...] = ()

    @field_validator("exponents")
    @classmethod
    def _canonicalize(cls, v: tuple[tuple[str, int], ...]) -> tuple[tuple[str, int], ...]:
        acc: dict[str, int] = {}
        for base, exp in v:
            acc[base] = acc.get(base, 0) + exp
        return tuple(sorted((b, e) for b, e in acc.items() if e != 0))

    @classmethod
    def base(cls, name: str) -> "Dimension":
        return cls(exponents=((name, 1),))

    @property
    def is_dimensionless(self) -> bool:
        return not self.exponents

    def __mul__(self, other: "Dimension") -> "Dimension":
        return Dimension(exponents=self.exponents + other.exponents)

    def __truediv__(self, other: "Dimension") -> "Dimension":
        return self * (other ** -1)

    def __pow__(self, n: int) -> "Dimension":
        return Dimension(exponents=tuple((b, e * n) for b, e in self.exponents))


DIMENSIONLESS = Dimension(exponents=())


def compatible(a: Dimension, b: Dimension) -> bool:
    """Two dimensions are compatible (addable/comparable) iff equal."""
    return a == b
```

- [ ] **Step 4: Export from `__init__.py`** — add `from .units import DIMENSIONLESS, Dimension, compatible`; add `"DIMENSIONLESS"`, `"Dimension"`, `"compatible"` to `__all__`.

- [ ] **Step 5: Run to verify PASS** — `uv run pytest tests/test_units.py -v` → expect 7 passed. Then `uv run pytest -q` → expect 84 (77 + 7).

- [ ] **Step 6: Commit + Progress Log** — `feat(grammar): Dimension units-of-measure abelian-group algebra`; append `- Task 3 ✅ Dimension algebra, commit <SHA>, 7 tests (84 total).`

---

### Task 4: wire `QuantityLeaf.dimension` (additive)

**Files:** Modify `leaf.py`; Test `grammar/tests/test_leaf_dimension.py`

- [ ] **Step 1: Write failing tests `grammar/tests/test_leaf_dimension.py`**

```python
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.units import Dimension


def test_quantity_without_dimension_still_builds():  # back-compat
    q = QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f")
    assert q.dimension is None


def test_quantity_with_dimension_builds():
    q = QuantityLeaf(value=37.0, unit="Cel", measurement_basis=MeasurementBasis.FUNDAMENTAL,
                     dimension=Dimension.base("temperature"))
    assert q.dimension == Dimension.base("temperature")


def test_quantity_with_dimension_is_hashable():
    q = QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f",
                     dimension=Dimension.base("length") / Dimension.base("time"))
    assert isinstance(hash(q), int)
```

- [ ] **Step 2: Run to verify FAIL** — `uv run pytest tests/test_leaf_dimension.py -v` → FAIL (extra="forbid" rejects `dimension`).

- [ ] **Step 3: Modify `grammar/src/polymer_grammar/leaf.py`**
- Add import (with the existing imports): `from .units import Dimension`
- Add a field to `QuantityLeaf`, after `formula`:
```python
    dimension: Dimension | None = None
```
Leave the `_basis_discipline` validator unchanged (dimension is independent of the unit/basis rule — optional metadata, allowed on any basis).

- [ ] **Step 4: Run to verify PASS (no regressions)** — `uv run pytest -v` → full suite **87** (84 + 3); prior leaf tests unaffected.

- [ ] **Step 5: Commit + Progress Log** — `feat(grammar): add optional QuantityLeaf.dimension (typed dimension alongside UCUM unit)`; append `- Task 4 ✅ QuantityLeaf.dimension wired, commit <SHA>, 3 tests (87 total).`

---

### Task 5: full gate + mark phase complete

- [ ] **Step 1: Run the gate** — `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -v && uv run ruff check src tests && uv run pytest tests/test_isolation.py -v`. Expect full suite green (~87), ruff clean, isolation PASS. Fix only `grammar/` files minimally if ruff flags anything; report the actual count.

- [ ] **Step 2: Mark phase complete + commit** — append `- Task 5 ✅ full gate (N green, ruff clean, isolation pass). **Phase 4 COMPLETE.**` then `docs(plan): Phase 4 complete`.

---

## Self-Review

**Spec coverage (against `2026-06-01-L2b-roles-and-units-spec.md`):**
- §1 Role enum + CausalRoles (predictor/outcome distinct; one-role-per-variable) + derived `adjustment_set` (= confounders, excludes mediators/colliders/instruments) → Task 1 ✓; wired into Claim → Task 2 ✓
- §2 Dimension abelian group (base/mul/div/pow/eq, normalization, DIMENSIONLESS, compatible) → Task 3 ✓; wired into QuantityLeaf → Task 4 ✓
- §4 acceptance (immutability/hashability via tuple reps, back-compat, full green, isolation) → Tasks 1–5 ✓

**Placeholder scan:** none — every code/test step complete; run steps have commands + expected counts (counts are estimates; executor reports actual).

**Type consistency:** `Role`/`CausalRoles`/`adjustment_set` consistent Task 1↔2; `Dimension`/`DIMENSIONLESS`/`compatible` consistent Task 3↔4; both new optional fields follow the additive pattern (`conclusion`/`licensing`); `model_validator` already imported in claim.py (Task 2 adds no field validator, so no new import needed there); leaf.py gains a `.units` import (no cycle — units.py imports only `.base`).

**Note for executor:** `Dimension` uses a sorted-tuple-of-pairs representation specifically so the frozen model stays HASHABLE (a `dict` field would make it unhashable and break `QuantityLeaf`/`Claim` hashability). Keep the `_canonicalize` validator — it's what makes equality structural and order-independent.
