# L1 — Molecular Proposition + Equivalence — Implementation Plan (Phase 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the claim conclusion a *molecular* identity — typed `Proposition` content + a version-pinned inferential neighborhood — and make "same claim?" an asserted, defeasible question via a lightweight `EquivalenceClaim` + transitive equivalence resolution.

**Architecture:** Additive to the existing isolated `grammar/` package (frozen pydantic v2 models). Two new modules (`proposition.py`, `equivalence.py`); one additive field on `Claim`. Identity is computed from *licensed equivalence edges*, never from hashes; the hashes are dedup/version handles only. TDD throughout.

**Tech Stack:** Python ≥3.12, pydantic v2, uv, pytest, ruff. Standard-library `hashlib` + `json` for content hashing.

**Source spec:** `docs/superpowers/specs/2026-06-01-L1-proposition-equivalence-spec.md`. Builds on Phase 1 (merged `8ffb666`).

---

## Progress Log

_(Append a dated entry per completed task: commit SHA + outcome + any deviation. Per working-preference: update this after every task.)_

- Not started.

---

## File Structure

```
grammar/src/polymer_grammar/
  proposition.py     # NEW: Direction, NeighborEdgeKind, NeighborEdge, Proposition (+ content_hash, neighborhood_hash)
  equivalence.py     # NEW: EquivalenceClaim, equivalence_class(), are_equivalent()
  claim.py           # MODIFY: add conclusion: Proposition | None = None
  __init__.py        # MODIFY: export new names (incrementally per task)
grammar/tests/
  test_proposition.py        # NEW
  test_equivalence.py        # NEW
  test_claim_conclusion.py   # NEW (conclusion wiring + Phase-1 back-compat)
```

Isolation invariant remains enforced by the existing `tests/test_isolation.py`.

---

### Task 1: `Proposition` — molecular conclusion content + hashes

**Files:**
- Create: `grammar/src/polymer_grammar/proposition.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_proposition.py`

- [ ] **Step 1: Write failing tests `grammar/tests/test_proposition.py`**

```python
import pytest

from polymer_grammar.proposition import (
    Direction,
    NeighborEdge,
    NeighborEdgeKind,
    Proposition,
)


def _prop(**kw):
    base = dict(direction=Direction.NEGATIVE, estimand="adjusted_effect_size",
                descriptor="curvature disfavors crossover after GC control")
    base.update(kw)
    return Proposition(**base)


def test_proposition_builds_with_typed_content():
    p = _prop()
    assert p.direction == Direction.NEGATIVE
    assert p.estimand == "adjusted_effect_size"
    assert p.neighborhood == ()


def test_content_hash_is_stable_and_independent_of_neighborhood():
    bare = _prop()
    with_nbr = _prop(neighborhood=(
        NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH, target="deadbeef"),
    ))
    # content_hash covers content only -> identical despite different neighborhoods
    assert bare.content_hash == with_nbr.content_hash
    assert _prop().content_hash == _prop().content_hash  # reproducible


def test_content_hash_changes_with_content():
    assert _prop().content_hash != _prop(direction=Direction.POSITIVE).content_hash


def test_neighborhood_hash_is_order_independent_and_sensitive_to_edges():
    e1 = NeighborEdge(kind=NeighborEdgeKind.ENTAILS, target="aaa")
    e2 = NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH, target="bbb")
    a = _prop(neighborhood=(e1, e2))
    b = _prop(neighborhood=(e2, e1))  # same set, different order
    assert a.neighborhood_hash == b.neighborhood_hash
    assert a.neighborhood_hash != _prop().neighborhood_hash  # empty differs


def test_proposition_is_hashable_and_neighborhood_immutable():
    p = _prop(neighborhood=(NeighborEdge(kind=NeighborEdgeKind.ENTAILS, target="x"),))
    assert isinstance(hash(p), int)
    assert isinstance(p.neighborhood, tuple)
    with pytest.raises(AttributeError):
        p.neighborhood.append(NeighborEdge(kind=NeighborEdgeKind.ENTAILS, target="y"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_proposition.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_grammar.proposition'`

- [ ] **Step 3: Create `grammar/src/polymer_grammar/proposition.py`**

```python
"""L1 — the molecular Proposition (spec §1.1; unified spec §3.2).

A claim's conclusion is molecular (Dummett): typed content PLUS a bounded,
version-pinned inferential neighborhood — its material-incompatibility / consequence
links to other propositions. Identity is NOT the byte-hash (Halvorson 2012); the
hashes below are dedup/cache + neighborhood-version handles only. "Same claim?" is
answered by an asserted, licensed EquivalenceClaim (see equivalence.py), never here.

The neighborhood's incompatible_with / entails edges are *material inference*
(meaning) — distinct from the L3 evidential defeat graph.
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum

from .base import _Model


class Direction(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NULL = "null"


class NeighborEdgeKind(str, Enum):
    INCOMPATIBLE_WITH = "incompatible_with"
    ENTAILS = "entails"


class NeighborEdge(_Model):
    kind: NeighborEdgeKind
    target: str  # content_hash of another Proposition
    label: str | None = None


def _sha(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class Proposition(_Model):
    direction: Direction
    estimand: str
    descriptor: str
    neighborhood: tuple[NeighborEdge, ...] = ()

    @property
    def content_hash(self) -> str:
        """Dedup/cache key over typed content only — NOT identity, NOT neighborhood."""
        return _sha(
            {
                "direction": self.direction.value,
                "estimand": self.estimand,
                "descriptor": self.descriptor,
            }
        )

    @property
    def neighborhood_hash(self) -> str:
        """Order-independent hash pinning the inferential-neighborhood version."""
        edges = sorted(
            (e.kind.value, e.target, e.label or "") for e in self.neighborhood
        )
        return _sha(edges)
```

- [ ] **Step 4: Export from `__init__.py`**

Add (keep existing exports + alphabetical tidiness):
```python
from .proposition import Direction, NeighborEdge, NeighborEdgeKind, Proposition
```
Add `"Direction"`, `"NeighborEdge"`, `"NeighborEdgeKind"`, `"Proposition"` to `__all__`.

- [ ] **Step 5: Run to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_proposition.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit + update Progress Log**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/
git commit -m "feat(grammar): L1 molecular Proposition (content + neighborhood + dedup/version hashes)"
```
Then append a Progress Log entry to this plan (Task 1 ✅ + SHA + "5 tests") and commit the doc:
```bash
git add docs/superpowers/plans/2026-06-01-L1-proposition-equivalence.md
git commit -m "docs(plan): L1 progress — Task 1 complete"
```

---

### Task 2: `EquivalenceClaim` — lightweight, defeasible

**Files:**
- Create: `grammar/src/polymer_grammar/equivalence.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_equivalence.py`

- [ ] **Step 1: Write failing tests `grammar/tests/test_equivalence.py`** (model invariants only; resolution functions are Task 3)

```python
import pytest
from pydantic import ValidationError

from polymer_grammar.equivalence import EquivalenceClaim
from polymer_grammar.status import PendingReason, Status


def _eq(**kw):
    base = dict(id="e1", left="hashA", right="hashB", severity=0.9,
                status=Status.LICENSED)
    base.update(kw)
    return EquivalenceClaim(**base)


def test_equivalence_builds():
    eq = _eq()
    assert eq.left == "hashA" and eq.right == "hashB"


def test_self_equivalence_rejected():
    with pytest.raises(ValidationError):
        _eq(left="same", right="same")


def test_severity_bounds_enforced():
    with pytest.raises(ValidationError):
        _eq(severity=1.5)


def test_pending_requires_reason():
    with pytest.raises(ValidationError):
        _eq(status=Status.PENDING)


def test_pending_reason_only_when_pending():
    with pytest.raises(ValidationError):
        _eq(status=Status.LICENSED, pending_reason=PendingReason.CONTESTED)


def test_pending_with_reason_ok():
    eq = _eq(status=Status.PENDING, pending_reason=PendingReason.CONTESTED)
    assert eq.pending_reason == PendingReason.CONTESTED
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_equivalence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'polymer_grammar.equivalence'`

- [ ] **Step 3: Create `grammar/src/polymer_grammar/equivalence.py`** (model + resolution functions; functions tested in Task 3)

```python
"""L1 — equivalence as an asserted, defeasible claim (spec §1.2-1.3).

"Same claim?" is answered by whether a LICENSED EquivalenceClaim relates two
propositions (by content_hash) — never by structural/hash equality (Halvorson 2012).
Lightweight first-class type now; promotable to a full meta-claim once
'subject = set of claims' exists. Only LICENSED edges count as "IN" (a stand-in for
L3 grounded-extension membership until the VAF layer lands).
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

from pydantic import Field, model_validator

from .base import _Model
from .status import PendingReason, Status


class EquivalenceClaim(_Model):
    id: str
    left: str
    right: str
    severity: float = Field(ge=0.0, le=1.0)
    status: Status
    pending_reason: PendingReason | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _distinct_endpoints(self) -> "EquivalenceClaim":
        if self.left == self.right:
            raise ValueError(
                "an EquivalenceClaim must relate two DISTINCT propositions"
            )
        return self

    @model_validator(mode="after")
    def _pending_reason_iff_pending(self) -> "EquivalenceClaim":
        if self.status == Status.PENDING and self.pending_reason is None:
            raise ValueError("status=PENDING requires a `pending_reason`")
        if self.status != Status.PENDING and self.pending_reason is not None:
            raise ValueError(
                f"`pending_reason` is only valid when status=PENDING; "
                f"got status={self.status.value}"
            )
        return self


def equivalence_class(
    handle: str, equivalences: Iterable[EquivalenceClaim]
) -> frozenset[str]:
    """Connected component of `handle` over LICENSED, symmetric equivalence edges
    (transitive closure). The component IS the equivalence_class_id material."""
    adj: dict[str, set[str]] = defaultdict(set)
    for eq in equivalences:
        if eq.status == Status.LICENSED:
            adj[eq.left].add(eq.right)
            adj[eq.right].add(eq.left)
    seen = {handle}
    queue: deque[str] = deque([handle])
    while queue:
        node = queue.popleft()
        for nbr in adj[node]:
            if nbr not in seen:
                seen.add(nbr)
                queue.append(nbr)
    return frozenset(seen)


def are_equivalent(
    a: str, b: str, equivalences: Iterable[EquivalenceClaim]
) -> bool:
    """Reflexive / symmetric / transitive over LICENSED equivalence edges."""
    return b in equivalence_class(a, equivalences)
```

- [ ] **Step 4: Export from `__init__.py`**

Add:
```python
from .equivalence import EquivalenceClaim, are_equivalent, equivalence_class
```
Add `"EquivalenceClaim"`, `"are_equivalent"`, `"equivalence_class"` to `__all__`.

- [ ] **Step 5: Run to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_equivalence.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit + update Progress Log**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/
git commit -m "feat(grammar): EquivalenceClaim (lightweight defeasible coreference assertion)"
git add docs/superpowers/plans/2026-06-01-L1-proposition-equivalence.md
git commit -m "docs(plan): L1 progress — Task 2 complete"
```
(Append the Progress Log entry before the second commit.)

---

### Task 3: equivalence resolution — `equivalence_class` + `are_equivalent`

The functions were written in Task 2 (they live in `equivalence.py`); this task **locks their behavior with tests** (transitivity, LICENSED-only, reflexive/symmetric).

**Files:**
- Test: `grammar/tests/test_equivalence.py` (append)

- [ ] **Step 1: Append failing tests to `grammar/tests/test_equivalence.py`**

```python
from polymer_grammar.equivalence import are_equivalent, equivalence_class


def _licensed(id_, a, b):
    return EquivalenceClaim(id=id_, left=a, right=b, severity=0.9,
                            status=Status.LICENSED)


def test_equivalence_class_is_transitive_over_licensed_edges():
    eqs = [_licensed("e1", "A", "B"), _licensed("e2", "B", "C")]
    assert equivalence_class("A", eqs) == frozenset({"A", "B", "C"})


def test_reflexive_even_with_no_edges():
    assert equivalence_class("solo", []) == frozenset({"solo"})
    assert are_equivalent("solo", "solo", [])


def test_symmetric():
    eqs = [_licensed("e1", "A", "B")]
    assert are_equivalent("A", "B", eqs)
    assert are_equivalent("B", "A", eqs)


def test_non_licensed_edges_do_not_merge_classes():
    pending = EquivalenceClaim(id="e1", left="A", right="B", severity=0.5,
                               status=Status.PENDING,
                               pending_reason=PendingReason.CONTESTED)
    rejected = EquivalenceClaim(id="e2", left="A", right="C", severity=0.1,
                                status=Status.REJECTED)
    assert equivalence_class("A", [pending, rejected]) == frozenset({"A"})
    assert not are_equivalent("A", "B", [pending, rejected])
```

- [ ] **Step 2: Run to verify the NEW tests pass** (functions already exist from Task 2)

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_equivalence.py -v`
Expected: PASS (10 passed total — 6 from Task 2 + 4 here)

- [ ] **Step 3: Commit + update Progress Log**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/
git commit -m "test(grammar): lock equivalence resolution (transitive, LICENSED-only, reflexive/symmetric)"
git add docs/superpowers/plans/2026-06-01-L1-proposition-equivalence.md
git commit -m "docs(plan): L1 progress — Task 3 complete"
```

---

### Task 4: wire `conclusion: Proposition | None` into `Claim` (additive, back-compat)

**Files:**
- Modify: `grammar/src/polymer_grammar/claim.py`
- Test: `grammar/tests/test_claim_conclusion.py`

- [ ] **Step 1: Write failing tests `grammar/tests/test_claim_conclusion.py`**

```python
from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.proposition import Direction, Proposition
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


def test_claim_without_conclusion_still_builds():  # Phase-1 back-compat
    assert _claim().conclusion is None


def test_claim_with_conclusion_builds():
    prop = Proposition(direction=Direction.NEGATIVE, estimand="adjusted_effect_size",
                       descriptor="curvature disfavors crossover after GC control")
    c = _claim(conclusion=prop)
    assert c.conclusion is prop
    assert c.conclusion.direction == Direction.NEGATIVE


def test_claim_with_conclusion_is_still_hashable():
    prop = Proposition(direction=Direction.NULL, estimand="x", descriptor="d")
    assert isinstance(hash(_claim(conclusion=prop)), int)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest tests/test_claim_conclusion.py -v`
Expected: FAIL (`TypeError`/`ValidationError` — `Claim` has no `conclusion` field / extra="forbid" rejects it)

- [ ] **Step 3: Modify `grammar/src/polymer_grammar/claim.py`**

Add the import and the field. After the existing imports add:
```python
from .proposition import Proposition
```
Add the field to `Claim` (immediately after `strength`):
```python
    conclusion: Proposition | None = None
```
(Leave everything else — including `_pending_reason_iff_pending` — unchanged. Update the module docstring's "Later phases add … the L1 molecular Proposition" line to note the conclusion is now wired.)

- [ ] **Step 4: Run to verify it passes (and no Phase-1 regressions)**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -v`
Expected: PASS — all prior tests + the 3 new ones (full suite should be **52**: 34 Phase-1 + 5 proposition + 10 equivalence + 3 conclusion).

- [ ] **Step 5: Commit + update Progress Log**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/
git commit -m "feat(grammar): wire optional conclusion: Proposition into Claim (additive, back-compat)"
git add docs/superpowers/plans/2026-06-01-L1-proposition-equivalence.md
git commit -m "docs(plan): L1 progress — Task 4 complete"
```

---

### Task 5: full-suite + ruff + isolation gate, and mark phase done

**Files:** none new (verification + Progress Log)

- [ ] **Step 1: Run the full suite + ruff + isolation guard**

Run: `cd /Users/zbb2/Desktop/polymer-claims/grammar && uv run pytest -v && uv run ruff check src tests && uv run pytest tests/test_isolation.py -v`
Expected: full suite green (52), ruff "All checks passed!", isolation guard PASS (the new modules must not import `polymer_formalclaim`). Fix any ruff issues minimally within `grammar/` only.

- [ ] **Step 2: Update Progress Log to "Phase 2 (L1) COMPLETE" and commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add docs/superpowers/plans/2026-06-01-L1-proposition-equivalence.md
git commit -m "docs(plan): L1 phase complete — 52 tests green"
```

---

## Self-Review

**Spec coverage (against `2026-06-01-L1-proposition-equivalence-spec.md`):**
- §1.1 Proposition (direction/estimand/descriptor + neighborhood + content_hash + neighborhood_hash, frozen+hashable, tuple neighborhood) → Task 1 ✓
- §1.2 EquivalenceClaim (refs + severity[0,1] + defeasible status + distinct-endpoints + PENDING↔reason invariants) → Task 2 ✓
- §1.3 equivalence_class (transitive, LICENSED-only) + are_equivalent (reflexive/symmetric/transitive) → Task 2 (impl) + Task 3 (locked by tests) ✓
- §1.4 Claim.conclusion optional/additive + Phase-1 back-compat → Task 4 ✓
- §3 acceptance criteria (stability/order-independence of hashes, immutability, back-compat, full green, isolation) → Tasks 1,4,5 ✓

**Placeholder scan:** none — every code step has complete code; every run step has exact command + expected count.

**Type consistency:** `Proposition`/`NeighborEdge`/`Direction`/`NeighborEdgeKind` consistent Task 1↔4; `EquivalenceClaim`/`equivalence_class`/`are_equivalent` consistent Task 2↔3; `Status`/`PendingReason` reused from Phase 1; `content_hash` is the agreed cross-reference handle (NeighborEdge.target and EquivalenceClaim.left/right all carry a Proposition content_hash string).

**Note for executor:** functions `equivalence_class`/`are_equivalent` are authored in Task 2's file creation but their behavior is *deliberately* locked by tests in Task 3 — this keeps Task 2 focused on the model and Task 3 on the algorithm; do not delete them from Task 2.
