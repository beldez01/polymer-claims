# `representation_revision` meta-tier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make schema/representation changes first-class licensable claims — an additive-optional `Claim.representation_revision` payload plus a pure "conservative bar" predicate the protocol enforces later. Completes all of Phase 7 and unblocks #5c RED-TEAM.

**Architecture:** A new grammar module `representation.py` (a `RevisionOperation` × discriminated `RevisionTarget` payload `RepresentationRevision` + the `meets_meta_tier_bar`/`is_representation_revision` helpers), wired as one additive-optional `Claim` field. Pure grammar slice — no protocol changes, Corpus untouched.

**Tech Stack:** Python 3.14, Pydantic v2 (frozen `_Model`, tuples, discriminated unions via `Annotated[..., Field(discriminator="kind")]`), `uv`, pytest, ruff. Package `polymer_grammar` (in `grammar/`).

**Spec:** `docs/superpowers/specs/2026-06-04-representation-revision-meta-tier-design.md`

---

## File Structure

- `grammar/src/polymer_grammar/representation.py` — **create**: operation enum, the 3 targets + `RevisionTarget` union, `RepresentationRevision` + validator, `meets_meta_tier_bar`/`is_representation_revision` + constants.
- `grammar/src/polymer_grammar/claim.py` — **modify**: import + one additive-optional field.
- `grammar/src/polymer_grammar/__init__.py` — **modify**: export the new symbols.
- `grammar/tests/test_representation.py` — **create**: module tests (targets, payload validators, `meets_meta_tier_bar`).
- `grammar/tests/test_claim_representation.py` — **create**: the additive-field back-compat + meta-claim + `is_representation_revision` cases (per the established `test_claim_<feature>.py` split).

Conventions (established): all models subclass `_Model` (frozen, `extra="forbid"`, tuple fields, hashable). Discriminated unions follow `subject.py`: `Annotated[A | B | C, Field(discriminator="kind")]`. `claim.py` imports each field type at module top. Tests for new symbols import from the MODULE path (`polymer_grammar.representation`) until Task 3 adds the package exports — mirroring how the #5a/#5b tests imported before their export task.

---

### Task 1: Grammar — `representation.py` module

**Files:**
- Create: `grammar/src/polymer_grammar/representation.py`
- Test: `grammar/tests/test_representation.py`

- [ ] **Step 1: Write the failing module tests**

Create `grammar/tests/test_representation.py`:

```python
import pytest
from pydantic import ValidationError

from polymer_grammar import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    PatternRef,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)
from polymer_grammar.representation import (
    META_TIER_ALLOWED_CLOSURES,
    META_TIER_REQUIRED_ROUTE,
    ConstraintTarget,
    OntologyTermTarget,
    PatternTarget,
    RepresentationRevision,
    RevisionOperation,
    meets_meta_tier_bar,
)

_PR = PatternRef(id="adjusted_effect", version="v1")
_PR2 = PatternRef(id="simple_correlation", version="v1")


def _rev(operation, target, rationale="because", proposed_definition=None):
    return RepresentationRevision(
        operation=operation, target=target, rationale=rationale,
        proposed_definition=proposed_definition,
    )


def test_add_pattern_builds():
    r = _rev(RevisionOperation.ADD, PatternTarget(patterns=(_PR,)))
    assert r.operation == RevisionOperation.ADD
    assert r.target.kind == "pattern"


def test_add_ontology_term_builds():
    r = _rev(RevisionOperation.ADD, OntologyTermTarget(term_id="HP:0001250"))
    assert r.target.kind == "ontology_term"


def test_deprecate_pattern_and_ontology_term_build():
    assert _rev(RevisionOperation.DEPRECATE, PatternTarget(patterns=(_PR,)))
    assert _rev(RevisionOperation.DEPRECATE, OntologyTermTarget(term_id="GO:0008150"))


def test_merge_requires_two_patterns():
    assert _rev(RevisionOperation.MERGE, PatternTarget(patterns=(_PR, _PR2)))
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.MERGE, PatternTarget(patterns=(_PR,)))  # only 1
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.MERGE, OntologyTermTarget(term_id="x"))  # not a pattern


def test_relax_requires_constraint_target():
    assert _rev(RevisionOperation.RELAX, ConstraintTarget(name="at_least_one_exclusion"))
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.RELAX, PatternTarget(patterns=(_PR,)))


def test_add_deprecate_reject_constraint_and_wrong_pattern_count():
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.ADD, ConstraintTarget(name="c"))
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.DEPRECATE, PatternTarget(patterns=(_PR, _PR2)))  # !=1


def test_rationale_required_nonempty():
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.ADD, OntologyTermTarget(term_id="x"), rationale="")


def test_empty_term_id_and_constraint_name_rejected():
    with pytest.raises(ValidationError):
        OntologyTermTarget(term_id="")
    with pytest.raises(ValidationError):
        ConstraintTarget(name="")


def test_target_dispatches_by_kind_from_dict():
    r = RepresentationRevision.model_validate(
        {"operation": "add", "target": {"kind": "ontology_term", "term_id": "HP:1"},
         "rationale": "x"}
    )
    assert isinstance(r.target, OntologyTermTarget)


def test_revision_is_hashable():
    r = _rev(RevisionOperation.ADD, OntologyTermTarget(term_id="x"))
    assert len({r, r}) == 1  # usable in a set -> content-addressable


def _lic(route, closure, n_mats, rivals=()):
    mats = [MaterializationContext(id=f"M{i}", api_version="v1", data_version="d1")
            for i in range(n_mats)]
    sats = tuple(Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=m) for m in mats)
    return Licensing(route=route, rival_set_closure=closure, rivals_considered=rivals, satisfactions=sats)


def test_meets_meta_tier_bar_true_cases():
    assert meets_meta_tier_bar(_lic(LicenseRoute.REPLICATION, RivalSetClosure.ENUMERATED, 2, ("r1",)))
    assert meets_meta_tier_bar(_lic(LicenseRoute.REPLICATION, RivalSetClosure.ONTOLOGY_BOUNDED, 2))


def test_meets_meta_tier_bar_false_cases():
    # severe test (single materialization) -> below the bar
    assert not meets_meta_tier_bar(_lic(LicenseRoute.SEVERE_TEST, RivalSetClosure.ENUMERATED, 1, ("r1",)))
    # replication but an OPEN rival closure -> below the bar
    assert not meets_meta_tier_bar(_lic(LicenseRoute.REPLICATION, RivalSetClosure.OPEN_ACKNOWLEDGED, 2))


def test_meta_tier_constants():
    assert META_TIER_REQUIRED_ROUTE == LicenseRoute.REPLICATION
    assert RivalSetClosure.ENUMERATED in META_TIER_ALLOWED_CLOSURES
    assert RivalSetClosure.ONTOLOGY_BOUNDED in META_TIER_ALLOWED_CLOSURES
    assert RivalSetClosure.OPEN_ACKNOWLEDGED not in META_TIER_ALLOWED_CLOSURES
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd grammar && uv run pytest tests/test_representation.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_grammar.representation'`.

- [ ] **Step 3: Create `representation.py`**

Create `grammar/src/polymer_grammar/representation.py`:

```python
"""representation_revision meta-tier (unified spec §5.5 / §7) — claims ABOUT the IR itself.

Schema/representation changes (new patterns, deprecated ontology terms, merged patterns, relaxed
constraints) are themselves claims, carried as an additive-optional `Claim.representation_revision`
payload so they reuse the full Claim machinery (status, licensing, provenance, defeat, AGM). The grammar
expresses the *more conservative* licensing bar as a pure predicate (`meets_meta_tier_bar`); the PROTOCOL
decides to enforce it (grammar represents, protocol decides). Imports nothing from polymer_protocol.

Deferred (noted in the spec): functorial migration of existing claims (§7 Spivak Δ/Σ/Π); schema_version
frozen-as-interpreted pinning; a reserved meta-pattern. `proposed_definition` is prose/JSON, not executable.
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field, model_validator

from .base import _Model
from .licensing import LicenseRoute, Licensing, RivalSetClosure
from .pattern import PatternRef

if TYPE_CHECKING:
    from .claim import Claim


class RevisionOperation(str, Enum):
    ADD = "add"
    DEPRECATE = "deprecate"
    MERGE = "merge"
    RELAX = "relax"


class PatternTarget(_Model):
    kind: Literal["pattern"] = "pattern"
    patterns: tuple[PatternRef, ...]  # exactly 1 for add/deprecate; >=2 for merge


class OntologyTermTarget(_Model):
    kind: Literal["ontology_term"] = "ontology_term"
    term_id: str = Field(min_length=1)


class ConstraintTarget(_Model):
    kind: Literal["constraint"] = "constraint"
    name: str = Field(min_length=1)


RevisionTarget = Annotated[
    PatternTarget | OntologyTermTarget | ConstraintTarget, Field(discriminator="kind")
]


class RepresentationRevision(_Model):
    operation: RevisionOperation
    target: RevisionTarget
    rationale: str = Field(min_length=1)       # a governed scientific act needs a justification
    proposed_definition: str | None = None     # new pattern/term content as prose/JSON (NOT executable)

    @model_validator(mode="after")
    def _operation_target_compatible(self) -> "RepresentationRevision":
        op, tgt = self.operation, self.target
        if op == RevisionOperation.MERGE:
            if not (isinstance(tgt, PatternTarget) and len(tgt.patterns) >= 2):
                raise ValueError("operation=merge requires a PatternTarget with >=2 patterns")
        elif op == RevisionOperation.RELAX:
            if not isinstance(tgt, ConstraintTarget):
                raise ValueError("operation=relax requires a ConstraintTarget")
        else:  # ADD / DEPRECATE
            if isinstance(tgt, ConstraintTarget):
                raise ValueError(f"operation={op.value} does not apply to a constraint target")
            if isinstance(tgt, PatternTarget) and len(tgt.patterns) != 1:
                raise ValueError(f"operation={op.value} on a pattern targets exactly 1 pattern")
        return self


META_TIER_REQUIRED_ROUTE = LicenseRoute.REPLICATION
META_TIER_ALLOWED_CLOSURES = frozenset(
    {RivalSetClosure.ENUMERATED, RivalSetClosure.ONTOLOGY_BOUNDED}
)


def meets_meta_tier_bar(licensing: Licensing) -> bool:
    """The conservative bar a representation-revision's licensing must clear: REPLICATION across independent
    materializations AND a CLOSED rival set (enumerated or ontology-bounded) — never a single severe test
    with an open-acknowledged closure. Pure; the PROTOCOL decides to enforce it (this slice gates nothing)."""
    return (
        licensing.route == META_TIER_REQUIRED_ROUTE
        and licensing.rival_set_closure in META_TIER_ALLOWED_CLOSURES
    )


def is_representation_revision(claim: "Claim") -> bool:
    """True iff `claim` carries a representation_revision payload (i.e. is a meta-tier claim)."""
    return claim.representation_revision is not None
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd grammar && uv run pytest tests/test_representation.py -q`
Expected: PASS (all module tests; `is_representation_revision` is exercised in Task 2 once the Claim field exists).

- [ ] **Step 5: Run the full grammar suite + ruff**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: all green (the new module is not yet imported by `claim.py` or the package `__init__`, so nothing else changes), ruff clean.

- [ ] **Step 6: Commit**

```bash
git add grammar/src/polymer_grammar/representation.py grammar/tests/test_representation.py
git commit -m "feat(grammar): representation_revision payload + meta-tier bar helpers (§5.5)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Grammar — wire `Claim.representation_revision`

**Files:**
- Modify: `grammar/src/polymer_grammar/claim.py`
- Test: `grammar/tests/test_claim_representation.py`

- [ ] **Step 1: Write the failing Claim-integration tests**

Create `grammar/tests/test_claim_representation.py`:

```python
from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.representation import (
    OntologyTermTarget,
    RepresentationRevision,
    RevisionOperation,
    is_representation_revision,
)
from polymer_grammar.status import Status


def _leaf():
    return QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f")


def _claim(**kw):
    base = dict(id="c", title="c", pattern=PatternRef(id="p", version="v1"),
                leaves=(_leaf(),), status=Status.CONJECTURED)
    base.update(kw)
    return Claim(**base)


def _rev():
    return RepresentationRevision(
        operation=RevisionOperation.ADD,
        target=OntologyTermTarget(term_id="HP:0001250"),
        rationale="needed to express the seizure phenotype",
    )


def test_representation_revision_is_optional_backcompat():
    c = _claim()
    assert c.representation_revision is None
    assert is_representation_revision(c) is False


def test_claim_carries_a_representation_revision():
    c = _claim(representation_revision=_rev())
    assert c.representation_revision is not None
    assert is_representation_revision(c) is True
    assert c.representation_revision.operation == RevisionOperation.ADD


def test_meta_claim_is_hashable_and_round_trips():
    c = _claim(representation_revision=_rev())
    hash(c)  # frozen + hashable must hold with the new field
    Claim.model_validate(c.model_dump())  # valid round-trip


def test_representation_revision_orthogonal_to_status():
    conj = _claim(status=Status.CONJECTURED, representation_revision=_rev())
    lic = _claim(status=Status.LICENSED, representation_revision=_rev())
    assert is_representation_revision(conj) and is_representation_revision(lic)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd grammar && uv run pytest tests/test_claim_representation.py -q`
Expected: FAIL — `Claim(...)` rejects the unexpected keyword `representation_revision` (the field doesn't exist yet; `extra="forbid"`).

- [ ] **Step 3: Add the field to `Claim`**

In `grammar/src/polymer_grammar/claim.py`, add the import (next to the other field-type imports, e.g. after `from .provenance import Provenance`):

```python
from .representation import RepresentationRevision
```

And add the additive-optional field to the `Claim` model (next to the other optional fields like `subject` / `governance`):

```python
    representation_revision: RepresentationRevision | None = None
```

(No present-only-when-Y validator — a meta-tier claim is conjectured→licensed like any claim.)

- [ ] **Step 4: Run to verify they pass**

Run: `cd grammar && uv run pytest tests/test_claim_representation.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Run the full grammar suite + ruff**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: all green (the field is additive-optional → no existing claim test breaks), ruff clean.

- [ ] **Step 6: Commit**

```bash
git add grammar/src/polymer_grammar/claim.py grammar/tests/test_claim_representation.py
git commit -m "feat(grammar): Claim.representation_revision additive field (meta-tier)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Grammar — package exports + full-suite green

**Files:**
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_representation.py`

- [ ] **Step 1: Write the failing export test**

Append to `grammar/tests/test_representation.py`:

```python
def test_representation_symbols_exported_from_package():
    import polymer_grammar as pg

    for name in (
        "RevisionOperation", "PatternTarget", "OntologyTermTarget", "ConstraintTarget",
        "RevisionTarget", "RepresentationRevision", "is_representation_revision",
        "meets_meta_tier_bar", "META_TIER_REQUIRED_ROUTE", "META_TIER_ALLOWED_CLOSURES",
    ):
        assert hasattr(pg, name), f"missing export: {name}"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd grammar && uv run pytest tests/test_representation.py::test_representation_symbols_exported_from_package -q`
Expected: FAIL — `AttributeError: module 'polymer_grammar' has no attribute 'RevisionOperation'`.

- [ ] **Step 3: Add the imports and `__all__` entries**

In `grammar/src/polymer_grammar/__init__.py`, add a `from .representation import (...)` block (next to the other module imports) bringing in all ten names, and add each to `__all__`:

```python
from .representation import (
    META_TIER_ALLOWED_CLOSURES,
    META_TIER_REQUIRED_ROUTE,
    ConstraintTarget,
    OntologyTermTarget,
    PatternTarget,
    RepresentationRevision,
    RevisionOperation,
    RevisionTarget,
    is_representation_revision,
    meets_meta_tier_bar,
)
```

```python
    "META_TIER_ALLOWED_CLOSURES",
    "META_TIER_REQUIRED_ROUTE",
    "ConstraintTarget",
    "OntologyTermTarget",
    "PatternTarget",
    "RepresentationRevision",
    "RevisionOperation",
    "RevisionTarget",
    "is_representation_revision",
    "meets_meta_tier_bar",
```

- [ ] **Step 4: Run the export test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_representation.py::test_representation_symbols_exported_from_package -q`
Expected: PASS.

- [ ] **Step 5: Run the full grammar suite + ruff + isolation**

Run: `cd grammar && uv run pytest -q && uv run ruff check src tests`
Expected: all green (existing grammar tests + new representation + claim-representation tests), ruff clean. `grammar/tests/test_isolation.py` still passes (grammar imports nothing from protocol / v1.2).

- [ ] **Step 6: Confirm the protocol suite is unaffected**

Run: `cd protocol && uv run pytest -q`
Expected: all green — this is an additive grammar change; the protocol writes only existing grammar IR and is unaffected.

- [ ] **Step 7: Commit**

```bash
git add grammar/src/polymer_grammar/__init__.py grammar/tests/test_representation.py
git commit -m "feat(grammar): export representation_revision meta-tier symbols (§5.5 — Phase 7 complete)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Progress Log

(Update after each task.)

- [ ] Task 1 — `representation.py` module
- [ ] Task 2 — `Claim.representation_revision` field
- [ ] Task 3 — package exports + full-suite green

## Self-review notes

- **Spec coverage:** the payload (`RevisionOperation` × discriminated `RevisionTarget` + `rationale`/`proposed_definition` + the (operation,target) validator) → Task 1; the conservative bar (`meets_meta_tier_bar` + constants) → Task 1; `is_representation_revision` → defined Task 1, tested Task 2 (needs the field); the additive `Claim` field (back-compat, hashable, round-trip, status-orthogonal) → Task 2; exports → Task 3. All spec test bullets map to a named test.
- **Import-order / circularity:** `representation.py` imports `.base`/`.pattern`/`.licensing` (none import it) at runtime, and `Claim` only under `TYPE_CHECKING`. `claim.py` imports `representation.py` at runtime — one-way, no cycle.
- **Fences honored:** functorial migration deferred (`proposed_definition` is prose/JSON); gate enforcement is protocol's job (grammar only ships the predicate); no `schema_version` pinning; protocol untouched.
- **Type consistency:** `RepresentationRevision(operation, target, rationale, proposed_definition=None)`; targets `PatternTarget(patterns=...)` / `OntologyTermTarget(term_id=...)` / `ConstraintTarget(name=...)`; `meets_meta_tier_bar(licensing) -> bool`; `is_representation_revision(claim) -> bool` — identical across plan, spec, tests.
- **Export-timing:** Task 1/2 tests import new symbols from `polymer_grammar.representation` (module path) since the package exports land in Task 3 — mirrors the #5a/#5b export sequencing.
