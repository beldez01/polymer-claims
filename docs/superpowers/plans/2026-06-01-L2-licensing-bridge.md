# L2 — Licensing Bridge — Implementation Plan (Phase 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement task-by-task. Steps use checkbox (`- [ ]`).

**Goal:** Let a claim *earn* LICENSED — model `(σ,M)` satisfaction, the dual route (severe_test | replication), and a required `rival_set_closure` — wired as an optional `Claim.licensing`.

**Architecture:** Additive to the isolated `grammar/` package (frozen pydantic v2 models, tuple fields). New module `licensing.py`; one optional field + one validator on `Claim`. Licensing-logic only (grounding node / agents deferred). TDD throughout.

**Tech Stack:** Python ≥3.12, pydantic v2, uv, pytest, ruff.

**Source spec:** `docs/superpowers/specs/2026-06-01-L2-licensing-bridge-spec.md`. Builds on Phase 1 + L1.

---

## Progress Log

_(Append a dated entry per completed task: commit SHA + outcome. Update after every task.)_

- 2026-06-01 — Task 1 ✅ satisfaction primitives, commit 7ddd839, 4 tests (58 total).
- 2026-06-01 — Task 2 ✅ Licensing record, commit 68a76d8, 6 tests (64 total).
- 2026-06-01 — Task 3 ✅ Claim.licensing wired, commit 97c05d6, 4 tests (68 total).

---

## File Structure

```
grammar/src/polymer_grammar/
  licensing.py   # NEW: SatisfactionVerdict, MaterializationContext, Satisfaction, LicenseRoute, RivalSetClosure, Licensing
  claim.py       # MODIFY: add licensing field + present-only-when-LICENSED validator
  __init__.py    # MODIFY: export new names
grammar/tests/
  test_licensing.py        # NEW
  test_claim_licensing.py  # NEW
```

---

### Task 1: `licensing.py` — satisfaction primitives

**Files:**
- Create: `grammar/src/polymer_grammar/licensing.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_licensing.py`

- [ ] **Step 1: Write failing tests `grammar/tests/test_licensing.py`**

```python
from polymer_grammar.licensing import (
    MaterializationContext,
    Satisfaction,
    SatisfactionVerdict,
)


def _m(id_="m1"):
    return MaterializationContext(id=id_, api_version="0.9.x", data_version="db@2026-06-01")


def test_materialization_context_carries_version_pins():
    m = _m()
    assert m.api_version == "0.9.x"
    assert m.data_version == "db@2026-06-01"


def test_satisfaction_always_pairs_verdict_with_materialization():
    s = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=_m())
    assert s.verdict == SatisfactionVerdict.SATISFIED
    assert s.materialization.id == "m1"


def test_satisfaction_is_hashable_and_immutable():
    s = Satisfaction(verdict=SatisfactionVerdict.REFUTED, materialization=_m())
    assert isinstance(hash(s), int)


def test_verdict_values():
    assert {v.value for v in SatisfactionVerdict} == {"satisfied", "refuted", "undetermined"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_licensing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_grammar.licensing'`

- [ ] **Step 3: Create `grammar/src/polymer_grammar/licensing.py`** (primitives only; `Licensing` added in Task 2)

```python
"""L2 — the licensing bridge (spec §1; unified spec §3.4).

How a claim EARNS the LICENSED status: satisfaction of its inference in a specific
materialization (the (σ, M) pair — never a context-free Boolean), reached via a
severe test OR replication across independent materializations, against a declared
closure of rival explanations. A licensing record cannot exist without naming its
rival-set closure — so no verdict is ever rendered LICENSED-simpliciter.

This phase models the licensing *logic*; the grounding node (produced_by /
licensed_by + asserting-agent) and the evaluator that *produces* satisfactions are
later phases.
"""
from __future__ import annotations

from enum import Enum

from .base import _Model


class SatisfactionVerdict(str, Enum):
    SATISFIED = "satisfied"
    REFUTED = "refuted"
    UNDETERMINED = "undetermined"


class MaterializationContext(_Model):
    id: str
    api_version: str
    data_version: str
    note: str | None = None


class Satisfaction(_Model):
    verdict: SatisfactionVerdict
    materialization: MaterializationContext
```

- [ ] **Step 4: Export from `__init__.py`**

Add `from .licensing import MaterializationContext, Satisfaction, SatisfactionVerdict` and add `"MaterializationContext"`, `"Satisfaction"`, `"SatisfactionVerdict"` to `__all__` (keep tidy).

- [ ] **Step 5: Run to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_licensing.py -v`
Expected: PASS (4 passed). Then full suite `uv run pytest -q` → expect 58 (54 + 4).

- [ ] **Step 6: Commit + Progress Log**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/
git commit -m "feat(grammar): L2 satisfaction primitives ((σ,M): verdict + materialization context)"
```
Append to Progress Log: `- 2026-06-01 — Task 1 ✅ satisfaction primitives, commit <SHA>, 4 tests (58 total).` then:
```bash
git add docs/superpowers/plans/2026-06-01-L2-licensing-bridge.md
git commit -m "docs(plan): L2 progress — Task 1 complete"
```

---

### Task 2: `Licensing` record + invariants

**Files:**
- Modify: `grammar/src/polymer_grammar/licensing.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_licensing.py` (append)

- [ ] **Step 1: Append failing tests to `grammar/tests/test_licensing.py`**

```python
import pytest
from pydantic import ValidationError

from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    RivalSetClosure,
)


def _sat(id_, verdict=SatisfactionVerdict.SATISFIED):
    return Satisfaction(verdict=verdict, materialization=_m(id_))


def test_severe_test_with_one_satisfied_materialization_builds():
    lic = Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(_sat("m1"),),
                    rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED)
    assert lic.route == LicenseRoute.SEVERE_TEST


def test_replication_requires_two_distinct_materializations():
    ok = Licensing(route=LicenseRoute.REPLICATION,
                   satisfactions=(_sat("m1"), _sat("m2")),
                   rival_set_closure=RivalSetClosure.ONTOLOGY_BOUNDED)
    assert len(ok.satisfactions) == 2
    with pytest.raises(ValidationError):  # only one M
        Licensing(route=LicenseRoute.REPLICATION, satisfactions=(_sat("m1"),),
                  rival_set_closure=RivalSetClosure.ONTOLOGY_BOUNDED)
    with pytest.raises(ValidationError):  # two satisfactions but same M id
        Licensing(route=LicenseRoute.REPLICATION,
                  satisfactions=(_sat("m1"), _sat("m1")),
                  rival_set_closure=RivalSetClosure.ONTOLOGY_BOUNDED)


def test_empty_satisfactions_rejected():
    with pytest.raises(ValidationError):
        Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(),
                  rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED)


def test_non_satisfied_satisfaction_rejected():
    with pytest.raises(ValidationError):
        Licensing(route=LicenseRoute.SEVERE_TEST,
                  satisfactions=(_sat("m1", SatisfactionVerdict.UNDETERMINED),),
                  rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED)


def test_enumerated_closure_requires_named_rivals():
    with pytest.raises(ValidationError):  # enumerated but no rivals listed
        Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(_sat("m1"),),
                  rival_set_closure=RivalSetClosure.ENUMERATED)
    ok = Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(_sat("m1"),),
                   rival_set_closure=RivalSetClosure.ENUMERATED,
                   rivals_considered=("MONDO:0005059",))
    assert ok.rivals_considered == ("MONDO:0005059",)


def test_licensing_is_hashable():
    lic = Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(_sat("m1"),),
                    rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED)
    assert isinstance(hash(lic), int)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_licensing.py -v`
Expected: FAIL with `ImportError: cannot import name 'Licensing'` (and `LicenseRoute`/`RivalSetClosure`).

- [ ] **Step 3: Add to `grammar/src/polymer_grammar/licensing.py`** (append after `Satisfaction`)

```python
from pydantic import model_validator


class LicenseRoute(str, Enum):
    SEVERE_TEST = "severe_test"
    REPLICATION = "replication"


class RivalSetClosure(str, Enum):
    ENUMERATED = "enumerated"
    ONTOLOGY_BOUNDED = "ontology_bounded"
    OPEN_ACKNOWLEDGED = "open_acknowledged"


class Licensing(_Model):
    route: LicenseRoute
    satisfactions: tuple[Satisfaction, ...]
    rival_set_closure: RivalSetClosure
    rivals_considered: tuple[str, ...] = ()
    note: str | None = None

    @model_validator(mode="after")
    def _all_satisfied(self) -> "Licensing":
        if not self.satisfactions:
            raise ValueError("a Licensing record requires >=1 satisfaction")
        if any(s.verdict != SatisfactionVerdict.SATISFIED for s in self.satisfactions):
            raise ValueError(
                "a Licensing record represents successful licensing; every "
                "satisfaction must be SATISFIED (refuted/undetermined => not licensed)"
            )
        return self

    @model_validator(mode="after")
    def _replication_needs_two_distinct_materializations(self) -> "Licensing":
        if self.route == LicenseRoute.REPLICATION:
            ids = {s.materialization.id for s in self.satisfactions}
            if len(ids) < 2:
                raise ValueError(
                    "route=replication requires >=2 satisfactions across DISTINCT "
                    "materializations (M1 ∧ M2)"
                )
        return self

    @model_validator(mode="after")
    def _enumerated_closure_names_rivals(self) -> "Licensing":
        if (
            self.rival_set_closure == RivalSetClosure.ENUMERATED
            and not self.rivals_considered
        ):
            raise ValueError(
                "rival_set_closure=enumerated requires a non-empty rivals_considered"
            )
        return self
```
(Move the `from pydantic import model_validator` to the top import block with the other imports rather than mid-file — keep imports clean.)

- [ ] **Step 4: Export from `__init__.py`**

Add `LicenseRoute, Licensing, RivalSetClosure` to the `from .licensing import ...` line and to `__all__`.

- [ ] **Step 5: Run to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_licensing.py -v`
Expected: PASS (10 passed: 4 + 6). Full suite `uv run pytest -q` → expect 64 (58 + 6).

- [ ] **Step 6: Commit + Progress Log**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/
git commit -m "feat(grammar): L2 Licensing record (dual route + rival_set_closure invariants)"
```
Append `- 2026-06-01 — Task 2 ✅ Licensing record, commit <SHA>, 6 tests (64 total).` then commit the doc.

---

### Task 3: wire `Claim.licensing` (additive, present-only-when-LICENSED)

**Files:**
- Modify: `grammar/src/polymer_grammar/claim.py`
- Test: `grammar/tests/test_claim_licensing.py`

- [ ] **Step 1: Write failing tests `grammar/tests/test_claim_licensing.py`**

```python
import pytest
from pydantic import ValidationError

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import Status


def _leaf():
    return QuantityLeaf(value=-0.238, measurement_basis=MeasurementBasis.DERIVED,
                        formula="ppcor::pcor.test(curvature, co_rate | gc)")


def _lic():
    sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED,
                       materialization=MaterializationContext(
                           id="m1", api_version="0.9.x", data_version="db@2026-06-01"))
    return Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(sat,),
                     rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED)


def _claim(**kw):
    base = dict(id="c", title="t",
                pattern=PatternRef(id="adjusted_effect", version="v1"),
                leaves=[_leaf()], status=Status.LICENSED)
    base.update(kw)
    return Claim(**base)


def test_licensed_claim_without_licensing_still_builds():  # additive back-compat
    assert _claim().licensing is None


def test_licensed_claim_with_licensing_builds():
    c = _claim(licensing=_lic())
    assert c.licensing.route == LicenseRoute.SEVERE_TEST


def test_licensing_on_non_licensed_claim_is_rejected():
    with pytest.raises(ValidationError):
        _claim(status=Status.CONJECTURED, licensing=_lic())


def test_claim_with_licensing_is_hashable():
    assert isinstance(hash(_claim(licensing=_lic())), int)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_claim_licensing.py -v`
Expected: FAIL — `Claim` has no `licensing` field (extra="forbid" rejects the kwarg).

- [ ] **Step 3: Modify `grammar/src/polymer_grammar/claim.py`**

Add import (with the other `.` imports):
```python
from .licensing import Licensing
```
Add the field after `conclusion`:
```python
    licensing: Licensing | None = None
```
Add a validator (after the existing `_pending_reason_iff_pending`):
```python
    @model_validator(mode="after")
    def _licensing_only_when_licensed(self) -> "Claim":
        if self.licensing is not None and self.status != Status.LICENSED:
            raise ValueError(
                f"`licensing` is only valid when status=LICENSED; "
                f"got status={self.status.value}"
            )
        return self
```
(Leave everything else unchanged. `model_validator` is already imported in claim.py.)

- [ ] **Step 4: Run to verify it passes (no regressions)**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -v`
Expected: PASS — full suite **68** (64 + 4). Confirm prior tests unaffected.

- [ ] **Step 5: Commit + Progress Log**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/
git commit -m "feat(grammar): wire optional Claim.licensing (present only when LICENSED, additive)"
```
Append `- 2026-06-01 — Task 3 ✅ Claim.licensing wired, commit <SHA>, 4 tests (68 total).` then commit the doc.

---

### Task 4: full gate + mark phase complete

- [ ] **Step 1: Run the gate**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -v && uv run ruff check src tests && uv run pytest tests/test_isolation.py -v`
Expected: full suite green (68), ruff "All checks passed!", isolation guard PASS. Fix only `grammar/` files minimally if ruff flags anything.

- [ ] **Step 2: Mark phase complete in Progress Log + commit**

Append `- 2026-06-01 — Task 4 ✅ full gate (68 green, ruff clean, isolation pass). **Phase 3 (L2) COMPLETE.**` then:
```bash
cd /Users/zbb2/Desktop/polymer-claims
git add docs/superpowers/plans/2026-06-01-L2-licensing-bridge.md
git commit -m "docs(plan): L2 phase complete"
```

---

## Self-Review

**Spec coverage (against `2026-06-01-L2-licensing-bridge-spec.md`):**
- §1 SatisfactionVerdict + MaterializationContext + Satisfaction ((σ,M), never a bare bool) → Task 1 ✓
- §1 Licensing + the 4 invariants (non-empty; all satisfied; replication ≥2 distinct M; enumerated⇒rivals) → Task 2 ✓
- §2 Claim.licensing additive + present-only-when-LICENSED; back-compat → Task 3 ✓
- §4 acceptance (immutability/hashability, full green, isolation) → Tasks 1–4 ✓

**Placeholder scan:** none — every code/test step is complete; run steps have exact commands + counts.

**Type consistency:** `SatisfactionVerdict`/`Satisfaction`/`MaterializationContext` consistent Task 1↔2↔3; `Licensing`/`LicenseRoute`/`RivalSetClosure` consistent Task 2↔3; `Status` reused from Phase 1; `model_validator` already imported in claim.py (Task 3 adds no new import for it).

**Note for executor:** in Task 3 Step 3, claim.py already imports `model_validator` (used by `_pending_reason_iff_pending`) — do not duplicate the import. The deferred hard gate ("LICENSED requires licensing") is intentionally NOT added here.
