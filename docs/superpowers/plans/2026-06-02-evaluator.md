# Phase 8 — Evaluator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the v1.3 grammar a runtime that executes a claim's typed compute graph against a materialization and **produces** L2 `Satisfaction`s — but only through an air-gapped, two-implementation agreement gate, so a claim can never license itself.

**Architecture:** Two new modules. `operations.py` is the declarative IR (a frozen, content-addressed typed compute DAG + satisfaction predicate) that travels with the claim via the additive-optional `Claim.evaluation_plan`. `evaluate.py` is the pure, adapter-injected runtime: `evaluate()` walks one implementation, `verify()` runs ≥2 distinct-identity adapters and mints a `Satisfaction` only on agreement. No infra imports — `test_isolation.py` stays green.

**Tech Stack:** Python 3.13+, pydantic v2 (frozen `_Model`, `extra="forbid"`), pytest, ruff, `uv`. Spec: `docs/superpowers/specs/2026-06-02-evaluator-spec.md`.

---

## File Structure

| File | Responsibility |
|---|---|
| `grammar/src/polymer_grammar/operations.py` | IR: `DataHandle`, `NodeRef`, `OpInput`, `ProducedLeafSpec`, `OperationNode`, `ComputeGraph`, `Comparator`, `SatisfactionCriterion`, `EvaluationPlan` |
| `grammar/src/polymer_grammar/claim.py` | Modify: add additive-optional `evaluation_plan` field |
| `grammar/src/polymer_grammar/evaluate.py` | Runtime: `ExecValue`, result models, `Adapter` Protocol, `SelfLicensingError`, reference adapters, `evaluate()`, `verify()` |
| `grammar/src/polymer_grammar/__init__.py` | Modify: export the new public symbols |
| `grammar/tests/test_operations.py` | IR validators, acyclicity, topo, content_hash, criterion |
| `grammar/tests/test_evaluate.py` | runtime execution, 3-valued criterion, drift, air-gap agreement/self-licensing/disagreement |

**Conventions to follow exactly** (verified against the existing package):
- All IR models subclass `_Model` from `.base` (already frozen + `extra="forbid"` + hashable).
- **No `dict`/`list` model fields** — use `tuple[...]`; key/value maps are `tuple[tuple[str, str], ...]`.
- `min_length` on collections/strings via `Field(min_length=...)`.
- `content_hash` mirrors `proposition.py`'s `_sha` (sha256 over `json.dumps(..., sort_keys=True, separators=(",", ":"))`).
- Tests import from the concrete module (`from polymer_grammar.operations import ...`) and use `pytest.raises(ValidationError)` for validator failures (see `tests/test_licensing.py`).
- Run tests: `cd grammar && uv run pytest -q`; lint: `uv run ruff check src tests`.

---

## Task 1: `operations.py` — inputs, produced-leaf spec, operation node

**Files:**
- Create: `grammar/src/polymer_grammar/operations.py`
- Test: `grammar/tests/test_operations.py`

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_operations.py
import pytest
from pydantic import ValidationError

from polymer_grammar.leaf import MeasurementBasis
from polymer_grammar.operations import (
    DataHandle,
    NodeRef,
    OperationNode,
    ProducedLeafSpec,
)
from polymer_grammar.units import Dimension


def _produces_quantity(**kw):
    base = dict(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED)
    base.update(kw)
    return ProducedLeafSpec(**base)


def test_data_handle_requires_nonempty_ref():
    h = DataHandle(ref="tcga:methylation:cg12345")
    assert h.kind == "data_handle"
    with pytest.raises(ValidationError):
        DataHandle(ref="")


def test_node_ref_carries_target():
    r = NodeRef(node_id="n1")
    assert r.kind == "node_ref"


def test_produced_spec_unit_only_for_fundamental_quantity():
    # FUNDAMENTAL + unit is fine
    ProducedLeafSpec(
        leaf_kind="quantity", measurement_basis=MeasurementBasis.FUNDAMENTAL, unit="m"
    )
    # DERIVED + unit is illegal (mirrors QuantityLeaf discipline)
    with pytest.raises(ValidationError):
        ProducedLeafSpec(
            leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED, unit="m"
        )


def test_produced_spec_nonquantity_forbids_unit_and_basis():
    ProducedLeafSpec(leaf_kind="categorical")
    with pytest.raises(ValidationError):
        ProducedLeafSpec(leaf_kind="categorical", unit="m")
    with pytest.raises(ValidationError):
        ProducedLeafSpec(leaf_kind="existence", measurement_basis=MeasurementBasis.DERIVED)


def test_operation_node_builds_with_mixed_inputs():
    node = OperationNode(
        id="corr",
        impl="python::scipy.stats.spearmanr",
        inputs=(DataHandle(ref="layer:col_x"), NodeRef(node_id="prep")),
        params=(("axis", "0"),),
        produces=_produces_quantity(dimension=Dimension(exponents=())),
    )
    assert node.id == "corr"
    assert node.inputs[0].kind == "data_handle"
    assert node.inputs[1].kind == "node_ref"
    assert node.oracle_ref is None  # declared-but-unbound slot for requirement #2


def test_operation_node_is_hashable():
    node = OperationNode(id="n", impl="builtin::const", produces=_produces_quantity())
    assert isinstance(hash(node), int)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_operations.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_grammar.operations'`

- [ ] **Step 3: Write minimal implementation**

```python
# grammar/src/polymer_grammar/operations.py
"""operations.py — the v1.3 operations IR (Phase 8; spec 2026-06-02-evaluator-spec.md §3).

A typed compute DAG: the declarative ("compiler-side") half of the compiler/runtime split —
HOW a claim is checked against data, expressed as DATA, not code. Each OperationNode names a
versioned `impl` dispatch key plus typed inputs (DataHandles into a materialization, or
NodeRefs to upstream outputs) and declares the TYPE of L0 Leaf it produces. The graph
terminates in a SatisfactionCriterion (see below) that turns the terminal output into a
3-valued verdict. The runtime that EXECUTES this lives in evaluate.py; this module ships only
the frozen, content-addressed type. Imports nothing from polymer_formalclaim and no infra.
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from .base import _Model
from .leaf import MeasurementBasis
from .units import Dimension


def _sha(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class DataHandle(_Model):
    """A REFERENCE to materializable data — never the data itself (air-gap)."""

    kind: Literal["data_handle"] = "data_handle"
    ref: str = Field(min_length=1)
    expected_dimension: Dimension | None = None


class NodeRef(_Model):
    """An edge to an upstream node's output."""

    kind: Literal["node_ref"] = "node_ref"
    node_id: str = Field(min_length=1)


OpInput = Annotated[Union[DataHandle, NodeRef], Field(discriminator="kind")]


class ProducedLeafSpec(_Model):
    """Declares the TYPE of L0 Leaf a node yields (not its value)."""

    leaf_kind: Literal["quantity", "categorical", "existence", "proposition"]
    measurement_basis: MeasurementBasis | None = None
    unit: str | None = None
    dimension: Dimension | None = None

    @model_validator(mode="after")
    def _basis_discipline(self) -> "ProducedLeafSpec":
        if self.leaf_kind != "quantity":
            if self.unit is not None or self.measurement_basis is not None:
                raise ValueError(
                    "unit/measurement_basis are only meaningful for quantity outputs; "
                    f"got leaf_kind={self.leaf_kind!r}"
                )
            return self
        if (
            self.unit is not None
            and self.measurement_basis != MeasurementBasis.FUNDAMENTAL
        ):
            raise ValueError(
                "unit is only meaningful for FUNDAMENTAL quantity outputs; "
                f"got unit={self.unit!r} with basis={self.measurement_basis}"
            )
        return self


class OperationNode(_Model):
    id: str = Field(min_length=1)
    impl: str = Field(min_length=1)
    inputs: tuple[OpInput, ...] = ()
    params: tuple[tuple[str, str], ...] = ()
    produces: ProducedLeafSpec
    oracle_ref: str | None = None  # declared-but-unbound slot for requirement #2
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_operations.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/operations.py grammar/tests/test_operations.py
git commit -m "feat(grammar): operations IR — DataHandle/NodeRef/ProducedLeafSpec/OperationNode"
```

---

## Task 2: `operations.py` — `ComputeGraph` (validators, topo order, content_hash)

**Files:**
- Modify: `grammar/src/polymer_grammar/operations.py` (append `ComputeGraph`)
- Test: `grammar/tests/test_operations.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to grammar/tests/test_operations.py
from polymer_grammar.operations import ComputeGraph


def _node(id_, impl="builtin::const", inputs=()):
    return OperationNode(
        id=id_, impl=impl, inputs=inputs, produces=_produces_quantity()
    )


def test_graph_builds_and_orders_topologically():
    g = ComputeGraph(
        nodes=(
            _node("a"),
            _node("b", inputs=(NodeRef(node_id="a"),)),
            _node("c", inputs=(NodeRef(node_id="b"),)),
        ),
        terminal="c",
    )
    assert g.topological_order == ("a", "b", "c")


def test_graph_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        ComputeGraph(nodes=(_node("a"), _node("a")), terminal="a")


def test_graph_rejects_dangling_noderef():
    with pytest.raises(ValidationError):
        ComputeGraph(
            nodes=(_node("a", inputs=(NodeRef(node_id="ghost"),)),), terminal="a"
        )


def test_graph_rejects_unknown_terminal():
    with pytest.raises(ValidationError):
        ComputeGraph(nodes=(_node("a"),), terminal="nope")


def test_graph_rejects_cycle():
    with pytest.raises(ValidationError):
        ComputeGraph(
            nodes=(
                _node("a", inputs=(NodeRef(node_id="b"),)),
                _node("b", inputs=(NodeRef(node_id="a"),)),
            ),
            terminal="a",
        )


def test_graph_requires_at_least_one_node():
    with pytest.raises(ValidationError):
        ComputeGraph(nodes=(), terminal="x")


def test_content_hash_is_stable_and_node_order_insensitive():
    g1 = ComputeGraph(
        nodes=(_node("a"), _node("b", inputs=(NodeRef(node_id="a"),))), terminal="b"
    )
    g2 = ComputeGraph(
        nodes=(_node("b", inputs=(NodeRef(node_id="a"),)), _node("a")), terminal="b"
    )
    assert g1.content_hash == g2.content_hash
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_operations.py -q`
Expected: FAIL — `ImportError: cannot import name 'ComputeGraph'`

- [ ] **Step 3: Write minimal implementation**

Append to `grammar/src/polymer_grammar/operations.py`:

```python
class ComputeGraph(_Model):
    nodes: tuple[OperationNode, ...] = Field(min_length=1)
    terminal: str = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> "ComputeGraph":
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"OperationNode ids must be unique; duplicates: {dupes}")
        return self

    @model_validator(mode="after")
    def _refs_resolve(self) -> "ComputeGraph":
        ids = {n.id for n in self.nodes}
        for n in self.nodes:
            for inp in n.inputs:
                if isinstance(inp, NodeRef) and inp.node_id not in ids:
                    raise ValueError(
                        f"node {n.id!r} references unknown node {inp.node_id!r}"
                    )
        if self.terminal not in ids:
            raise ValueError(f"terminal {self.terminal!r} is not a node id")
        return self

    @model_validator(mode="after")
    def _acyclic(self) -> "ComputeGraph":
        remaining = {n.id: self._deps(n) for n in self.nodes}
        seen: set[str] = set()
        progress = True
        while progress:
            progress = False
            for nid, d in list(remaining.items()):
                if d <= seen:
                    seen.add(nid)
                    del remaining[nid]
                    progress = True
        if remaining:
            raise ValueError(
                "ComputeGraph must be acyclic (NodeRef edges form a cycle): "
                f"{sorted(remaining)}"
            )
        return self

    @staticmethod
    def _deps(node: OperationNode) -> set[str]:
        return {inp.node_id for inp in node.inputs if isinstance(inp, NodeRef)}

    @property
    def topological_order(self) -> tuple[str, ...]:
        """Deterministic topo sort; ties broken by declaration order (reproducible)."""
        order_index = {n.id: i for i, n in enumerate(self.nodes)}
        remaining = {n.id: self._deps(n) for n in self.nodes}
        out: list[str] = []
        placed: set[str] = set()
        while remaining:
            ready = sorted(
                (nid for nid, d in remaining.items() if d <= placed),
                key=lambda nid: order_index[nid],
            )
            nxt = ready[0]
            out.append(nxt)
            placed.add(nxt)
            del remaining[nxt]
        return tuple(out)

    @property
    def content_hash(self) -> str:
        """SHA-256 over canonical node content; node-declaration-order insensitive."""
        node_dicts = sorted(
            (
                {
                    "id": n.id,
                    "impl": n.impl,
                    "inputs": [inp.model_dump(mode="json") for inp in n.inputs],
                    "params": [list(p) for p in n.params],
                    "produces": n.produces.model_dump(mode="json"),
                    "oracle_ref": n.oracle_ref,
                }
                for n in self.nodes
            ),
            key=lambda d: d["id"],
        )
        return _sha({"terminal": self.terminal, "nodes": node_dicts})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_operations.py -q`
Expected: PASS (13 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/operations.py grammar/tests/test_operations.py
git commit -m "feat(grammar): ComputeGraph — acyclic/unique/resolvable validators + topo + content_hash"
```

---

## Task 3: `operations.py` — `Comparator`, `SatisfactionCriterion`, `EvaluationPlan`

**Files:**
- Modify: `grammar/src/polymer_grammar/operations.py` (append)
- Test: `grammar/tests/test_operations.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to grammar/tests/test_operations.py
from polymer_grammar.operations import (
    Comparator,
    EvaluationPlan,
    SatisfactionCriterion,
)


def test_criterion_threshold_route_builds():
    c = SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05)
    assert c.comparator == Comparator.LT


def test_criterion_reference_route_builds():
    c = SatisfactionCriterion(comparator=Comparator.GE, reference_leaf_index=0)
    assert c.reference_leaf_index == 0


def test_criterion_requires_exactly_one_target():
    with pytest.raises(ValidationError):  # neither
        SatisfactionCriterion(comparator=Comparator.LT)
    with pytest.raises(ValidationError):  # both
        SatisfactionCriterion(
            comparator=Comparator.LT, threshold=0.05, reference_leaf_index=0
        )


def test_within_tol_requires_tolerance():
    SatisfactionCriterion(
        comparator=Comparator.WITHIN_TOL, threshold=1.0, tolerance=0.01
    )
    with pytest.raises(ValidationError):
        SatisfactionCriterion(comparator=Comparator.WITHIN_TOL, threshold=1.0)


def test_negative_reference_index_rejected():
    with pytest.raises(ValidationError):
        SatisfactionCriterion(comparator=Comparator.LT, reference_leaf_index=-1)


def test_evaluation_plan_bundles_graph_and_criterion():
    g = ComputeGraph(nodes=(_node("a"),), terminal="a")
    plan = EvaluationPlan(
        graph=g, criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=1.0)
    )
    assert plan.graph.terminal == "a"
    assert isinstance(hash(plan), int)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_operations.py -q`
Expected: FAIL — `ImportError: cannot import name 'Comparator'`

- [ ] **Step 3: Write minimal implementation**

Append to `grammar/src/polymer_grammar/operations.py`:

```python
class Comparator(str, Enum):
    LT = "lt"
    LE = "le"
    EQ = "eq"
    NE = "ne"
    GE = "ge"
    GT = "gt"
    WITHIN_TOL = "within_tol"


class SatisfactionCriterion(_Model):
    comparator: Comparator
    threshold: float | None = None
    reference_leaf_index: int | None = Field(default=None, ge=0)
    tolerance: float | None = None

    @model_validator(mode="after")
    def _exactly_one_target(self) -> "SatisfactionCriterion":
        has_thr = self.threshold is not None
        has_ref = self.reference_leaf_index is not None
        if has_thr == has_ref:
            raise ValueError(
                "SatisfactionCriterion requires exactly one of `threshold` or "
                "`reference_leaf_index`"
            )
        return self

    @model_validator(mode="after")
    def _within_tol_needs_tolerance(self) -> "SatisfactionCriterion":
        if self.comparator == Comparator.WITHIN_TOL and self.tolerance is None:
            raise ValueError("comparator=within_tol requires a `tolerance`")
        return self


class EvaluationPlan(_Model):
    graph: ComputeGraph
    criterion: SatisfactionCriterion
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_operations.py -q`
Expected: PASS (19 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/operations.py grammar/tests/test_operations.py
git commit -m "feat(grammar): SatisfactionCriterion (exactly-one-target, within_tol) + EvaluationPlan"
```

---

## Task 4: Wire `Claim.evaluation_plan` + export operations public API

**Files:**
- Modify: `grammar/src/polymer_grammar/claim.py`
- Modify: `grammar/src/polymer_grammar/__init__.py`
- Test: `grammar/tests/test_claim_evaluation_plan.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_claim_evaluation_plan.py
from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.operations import (
    Comparator,
    ComputeGraph,
    EvaluationPlan,
    OperationNode,
    ProducedLeafSpec,
    SatisfactionCriterion,
)
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import Status


def _leaf():
    return QuantityLeaf(
        value=0.03, measurement_basis=MeasurementBasis.DERIVED, formula="x"
    )


def _plan():
    node = OperationNode(
        id="a",
        impl="builtin::const",
        params=(("value", "0.03"),),
        produces=ProducedLeafSpec(
            leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED
        ),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="a"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
    )


def test_claim_without_plan_still_builds():
    claim = Claim(
        id="c", title="t", pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=[_leaf()], status=Status.CONJECTURED,
    )
    assert claim.evaluation_plan is None


def test_claim_carries_evaluation_plan():
    claim = Claim(
        id="c", title="t", pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=[_leaf()], status=Status.CONJECTURED, evaluation_plan=_plan(),
    )
    assert claim.evaluation_plan.graph.terminal == "a"


def test_operations_public_api_is_exported():
    import polymer_grammar as pg

    for name in (
        "DataHandle", "NodeRef", "OperationNode", "ProducedLeafSpec",
        "ComputeGraph", "Comparator", "SatisfactionCriterion", "EvaluationPlan",
    ):
        assert hasattr(pg, name), name
```

Note: confirm `Status.CONJECTURED` exists (it does — see `status.py`). If the exact member name differs, use the lifecycle's initial status from `status.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_claim_evaluation_plan.py -q`
Expected: FAIL — `AttributeError`/`TypeError` on `evaluation_plan` (field not yet on `Claim`)

- [ ] **Step 3: Write minimal implementation**

In `grammar/src/polymer_grammar/claim.py`, add the import (with the other `from .` imports) and the field (after `governance`):

```python
from .operations import EvaluationPlan
```
```python
    governance: Governance | None = None
    evaluation_plan: EvaluationPlan | None = None
```

In `grammar/src/polymer_grammar/__init__.py`, add the import block (after the `.governance` import) and extend `__all__`:

```python
from .operations import (
    Comparator,
    ComputeGraph,
    DataHandle,
    EvaluationPlan,
    NodeRef,
    OperationNode,
    OpInput,
    ProducedLeafSpec,
    SatisfactionCriterion,
)
```
Add these strings to the `__all__` list:
```python
    "Comparator",
    "ComputeGraph",
    "DataHandle",
    "EvaluationPlan",
    "NodeRef",
    "OperationNode",
    "OpInput",
    "ProducedLeafSpec",
    "SatisfactionCriterion",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_claim_evaluation_plan.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/claim.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_claim_evaluation_plan.py
git commit -m "feat(grammar): additive-optional Claim.evaluation_plan + export operations API"
```

---

## Task 5: `evaluate.py` — result models, `Adapter` Protocol, reference adapters

**Files:**
- Create: `grammar/src/polymer_grammar/evaluate.py`
- Test: `grammar/tests/test_evaluate.py`

- [ ] **Step 1: Write the failing test**

```python
# grammar/tests/test_evaluate.py
from polymer_grammar.evaluate import (
    ExecValue,
    IdentityAdapter,
    ReferenceAdapter,
    SelfLicensingError,
)
from polymer_grammar.leaf import MeasurementBasis
from polymer_grammar.licensing import MaterializationContext
from polymer_grammar.operations import OperationNode, ProducedLeafSpec


def _ctx():
    return MaterializationContext(
        id="m1", api_version="0.9.x", data_version="db@2026-06-02"
    )


def _q():
    return ProducedLeafSpec(
        leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED
    )


def test_exec_value_holds_scalar():
    assert ExecValue(value=1.5).value == 1.5
    assert ExecValue(value=None).value is None


def test_self_licensing_error_exists():
    assert issubclass(SelfLicensingError, Exception)


def test_const_impl_agrees_across_two_implementations():
    node = OperationNode(
        id="a", impl="builtin::const", params=(("value", "0.03"),), produces=_q()
    )
    a = IdentityAdapter()
    b = ReferenceAdapter()
    assert a.identity != b.identity
    va = a.execute(node, (), _ctx())
    vb = b.execute(node, (), _ctx())
    assert va.value == vb.value == 0.03


def test_mean_impl_computed_independently_agrees():
    node = OperationNode(
        id="a", impl="builtin::mean", params=(("vector", "1,2,3,4"),), produces=_q()
    )
    va = IdentityAdapter().execute(node, (), _ctx())
    vb = ReferenceAdapter().execute(node, (), _ctx())
    assert va.value == vb.value == 2.5


def test_perturbed_reference_adapter_disagrees():
    node = OperationNode(
        id="a", impl="builtin::const", params=(("value", "0.03"),), produces=_q()
    )
    vb = ReferenceAdapter(perturb=1.0).execute(node, (), _ctx())
    assert vb.value == 1.03
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_evaluate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_grammar.evaluate'`

- [ ] **Step 3: Write minimal implementation**

```python
# grammar/src/polymer_grammar/evaluate.py
"""evaluate.py — the v1.3 evaluator runtime (Phase 8; spec §4).

The "runtime" half of the compiler/runtime split: executes a claim's EvaluationPlan
(operations.py) against a MaterializationContext and PRODUCES the L2 Satisfaction that the
static Licensing record consumes — but only through an air-gapped, two-implementation
agreement gate (`verify`), so a claim can never license itself. Pure + adapter-injected;
imports NO infra (no network/R/scipy). Real adapters live OUTSIDE this package; the reference
adapters here are deterministic and exist to exercise the plumbing + the air-gap.
"""
from __future__ import annotations

import statistics
from typing import Literal, Protocol

from .base import _Model
from .leaf import Leaf
from .licensing import MaterializationContext, Satisfaction, SatisfactionVerdict
from .operations import EvaluationPlan, NodeRef, OperationNode
from .units import Dimension


class SelfLicensingError(Exception):
    """Raised by `verify` when fewer than 2 DISTINCT adapter identities are supplied —
    the structural 'no self-licensing' air-gap (writer must not be the verifier)."""


class ExecValue(_Model):
    """The value an operation node produces, carried between nodes and into the criterion."""

    value: float | str | None = None
    dimension: Dimension | None = None


class Drift(_Model):
    pinned: float | str | None = None
    computed: float | str | None = None
    abs_diff: float | None = None
    rel_diff: float | None = None
    within_tolerance: bool | None = None


class NodeEvaluation(_Model):
    node_id: str
    impl: str
    produced: Leaf | None = None
    drift: Drift | None = None
    error: str | None = None


class EvaluationResult(_Model):
    verdict: SatisfactionVerdict
    terminal: ExecValue
    nodes: tuple[NodeEvaluation, ...]
    adapter_identity: str
    status: Literal["complete", "partial", "error"]


class VerifiedEvaluation(_Model):
    results: tuple[EvaluationResult, ...]
    agreement: bool
    satisfaction: Satisfaction | None = None
    disagreement: str | None = None


class Adapter(Protocol):
    """The materialization/compute boundary. `identity` drives the air-gap gate.

    `execute` receives the node, the already-executed ExecValues of the node's NodeRef
    inputs (in input order), and the materialization context. Resolving DataHandle inputs
    is the adapter's own responsibility (real adapters hit the API; reference adapters read
    deterministic params).
    """

    identity: str

    def execute(
        self,
        node: OperationNode,
        upstream: tuple[ExecValue, ...],
        ctx: MaterializationContext,
    ) -> ExecValue: ...


def _params(node: OperationNode) -> dict[str, str]:
    return {k: v for k, v in node.params}


class IdentityAdapter:
    """Reference impl A — straightforward arithmetic. End-to-end smoke target."""

    identity = "identity"

    def execute(
        self,
        node: OperationNode,
        upstream: tuple[ExecValue, ...],
        ctx: MaterializationContext,
    ) -> ExecValue:
        p = _params(node)
        if node.impl in ("builtin::const",):
            return ExecValue(value=float(p["value"]))
        if node.impl == "builtin::identity":
            return upstream[0] if upstream else ExecValue(value=float(p["value"]))
        if node.impl == "builtin::mean":
            xs = [float(x) for x in p["vector"].split(",")]
            return ExecValue(value=sum(xs) / len(xs))
        raise ValueError(f"IdentityAdapter has no handler for impl {node.impl!r}")


class ReferenceAdapter:
    """Reference impl B — independently coded (stdlib `statistics`) so agreement across
    A and B is a genuine two-implementation check. `perturb` adds a constant to numeric
    outputs to drive the disagreement test."""

    def __init__(self, identity: str = "reference", perturb: float = 0.0) -> None:
        self.identity = identity
        self.perturb = perturb

    def execute(
        self,
        node: OperationNode,
        upstream: tuple[ExecValue, ...],
        ctx: MaterializationContext,
    ) -> ExecValue:
        p = _params(node)
        if node.impl == "builtin::const":
            out = float(p["value"])
        elif node.impl == "builtin::identity":
            if upstream:
                base = upstream[0].value
                out = float(base) if isinstance(base, (int, float)) else base
            else:
                out = float(p["value"])
        elif node.impl == "builtin::mean":
            out = statistics.fmean(float(x) for x in p["vector"].split(","))
        else:
            raise ValueError(f"ReferenceAdapter has no handler for impl {node.impl!r}")
        if self.perturb and isinstance(out, (int, float)):
            out = float(out) + self.perturb
        return ExecValue(value=out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_evaluate.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/evaluate.py grammar/tests/test_evaluate.py
git commit -m "feat(grammar): evaluate.py result models + Adapter Protocol + two reference adapters"
```

---

## Task 6: `evaluate.py` — `evaluate()` single-implementation runtime

**Files:**
- Modify: `grammar/src/polymer_grammar/evaluate.py` (append helpers + `evaluate`)
- Test: `grammar/tests/test_evaluate.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to grammar/tests/test_evaluate.py
from polymer_grammar.evaluate import evaluate
from polymer_grammar.leaf import QuantityLeaf
from polymer_grammar.operations import (
    Comparator,
    ComputeGraph,
    EvaluationPlan,
    SatisfactionCriterion,
)
from polymer_grammar.licensing import SatisfactionVerdict
from polymer_grammar.units import Dimension


def _plan(impl="builtin::const", params=(("value", "0.03"),), criterion=None):
    node = OperationNode(id="a", impl=impl, params=params, produces=_q())
    if criterion is None:
        criterion = SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05)
    return EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="a"), criterion=criterion)


def test_evaluate_satisfied_below_threshold():
    res = evaluate(_plan(), _ctx(), IdentityAdapter())
    assert res.verdict == SatisfactionVerdict.SATISFIED
    assert res.terminal.value == 0.03
    assert res.status == "complete"
    assert res.adapter_identity == "identity"


def test_evaluate_refuted_above_threshold():
    res = evaluate(_plan(params=(("value", "0.9"),)), _ctx(), IdentityAdapter())
    assert res.verdict == SatisfactionVerdict.REFUTED


def test_evaluate_undetermined_on_node_error():
    # 'builtin::nope' has no handler -> node errors -> terminal None -> UNDETERMINED
    res = evaluate(_plan(impl="builtin::nope"), _ctx(), IdentityAdapter())
    assert res.verdict == SatisfactionVerdict.UNDETERMINED
    assert res.status == "error"
    assert res.nodes[0].error is not None


def test_evaluate_records_drift_against_expected_param():
    plan = _plan(params=(("value", "0.03"), ("expected", "0.03")))
    res = evaluate(plan, _ctx(), IdentityAdapter())
    assert res.nodes[0].drift is not None
    assert res.nodes[0].drift.within_tolerance is True


def test_evaluate_wraps_typed_leaf():
    res = evaluate(_plan(), _ctx(), IdentityAdapter())
    assert isinstance(res.nodes[0].produced, QuantityLeaf)
    assert res.nodes[0].produced.value == 0.03


def test_evaluate_reference_leaf_comparison_with_dimension_mismatch():
    # terminal carries a dimension; reference leaf carries an incompatible one
    node = OperationNode(
        id="a", impl="builtin::const", params=(("value", "1.0"),),
        produces=ProducedLeafSpec(
            leaf_kind="quantity", measurement_basis=MeasurementBasis.FUNDAMENTAL,
            unit="m", dimension=Dimension.base("length"),
        ),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="a"),
        criterion=SatisfactionCriterion(comparator=Comparator.GE, reference_leaf_index=0),
    )
    ref_leaf = QuantityLeaf(
        value=0.5, unit="s", measurement_basis=MeasurementBasis.FUNDAMENTAL,
        dimension=Dimension.base("time"),
    )
    res = evaluate(plan, _ctx(), IdentityAdapter(), claim_leaves=(ref_leaf,))
    assert res.verdict == SatisfactionVerdict.UNDETERMINED


def test_evaluate_reference_leaf_comparison_satisfied():
    node = OperationNode(
        id="a", impl="builtin::const", params=(("value", "2.0"),), produces=_q()
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="a"),
        criterion=SatisfactionCriterion(comparator=Comparator.GT, reference_leaf_index=0),
    )
    ref_leaf = QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="x")
    res = evaluate(plan, _ctx(), IdentityAdapter(), claim_leaves=(ref_leaf,))
    assert res.verdict == SatisfactionVerdict.SATISFIED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_evaluate.py -q`
Expected: FAIL — `ImportError: cannot import name 'evaluate'`

- [ ] **Step 3: Write minimal implementation**

Append to `grammar/src/polymer_grammar/evaluate.py` (add the extra imports at the top of the file alongside the existing ones):

```python
# add to the existing imports near the top:
from .leaf import (
    CategoricalLeaf,
    ExistenceLeaf,
    MeasurementBasis,
    PropositionLeaf,
    QuantityLeaf,
)
from .operations import Comparator, SatisfactionCriterion
from .units import compatible
```

```python
_ABS_TOL = 1e-9
_REL_TOL = 1e-6


def _wrap_leaf(spec, value: float | str | None) -> Leaf | None:
    if value is None:
        return None
    if spec.leaf_kind == "quantity":
        basis = spec.measurement_basis or MeasurementBasis.DERIVED
        formula = "evaluator::computed" if basis == MeasurementBasis.DERIVED else None
        return QuantityLeaf(
            value=float(value),
            unit=spec.unit,
            measurement_basis=basis,
            formula=formula,
            dimension=spec.dimension,
        )
    if spec.leaf_kind == "categorical":
        return CategoricalLeaf(ontology_term=str(value))
    if spec.leaf_kind == "existence":
        state = value if value in ("observed", "not_detected") else "observed"
        return ExistenceLeaf(state=state)  # type: ignore[arg-type]
    return PropositionLeaf(data=str(value), warrant="evaluator::computed")


def _drift(expected: str | None, computed: float | str | None) -> Drift | None:
    if expected is None:
        return None
    try:
        pinned = float(expected)
    except ValueError:
        return None
    if not isinstance(computed, (int, float)):
        return None
    ad = abs(pinned - float(computed))
    denom = max(abs(pinned), abs(float(computed)), 1.0)
    rd = ad / denom
    return Drift(
        pinned=pinned,
        computed=computed,
        abs_diff=ad,
        rel_diff=rd,
        within_tolerance=(ad <= _ABS_TOL or rd <= _REL_TOL),
    )


def _resolve_reference(
    criterion: SatisfactionCriterion, claim_leaves: tuple[Leaf, ...]
) -> tuple[float | str | None, Dimension | None, str | None]:
    if criterion.reference_leaf_index is None:
        return criterion.threshold, None, None
    idx = criterion.reference_leaf_index
    if idx >= len(claim_leaves):
        return None, None, f"reference_leaf_index {idx} out of range (have {len(claim_leaves)})"
    leaf = claim_leaves[idx]
    if isinstance(leaf, QuantityLeaf):
        return leaf.value, leaf.dimension, None
    if isinstance(leaf, CategoricalLeaf):
        return leaf.ontology_term, None, None
    return None, None, f"reference leaf kind {leaf.kind!r} is not comparable"


def _apply_criterion(
    criterion: SatisfactionCriterion,
    terminal: ExecValue,
    claim_leaves: tuple[Leaf, ...],
) -> SatisfactionVerdict:
    rhs, rhs_dim, err = _resolve_reference(criterion, claim_leaves)
    if err is not None:
        return SatisfactionVerdict.UNDETERMINED
    lhs = terminal.value
    if lhs is None or rhs is None:
        return SatisfactionVerdict.UNDETERMINED
    if (
        criterion.reference_leaf_index is not None
        and terminal.dimension is not None
        and rhs_dim is not None
        and not compatible(terminal.dimension, rhs_dim)
    ):
        return SatisfactionVerdict.UNDETERMINED
    cmp = criterion.comparator
    if isinstance(lhs, str) or isinstance(rhs, str):
        if cmp == Comparator.EQ:
            ok = lhs == rhs
        elif cmp == Comparator.NE:
            ok = lhs != rhs
        else:
            return SatisfactionVerdict.UNDETERMINED
        return SatisfactionVerdict.SATISFIED if ok else SatisfactionVerdict.REFUTED
    left, right = float(lhs), float(rhs)
    if cmp == Comparator.LT:
        ok = left < right
    elif cmp == Comparator.LE:
        ok = left <= right
    elif cmp == Comparator.EQ:
        ok = left == right
    elif cmp == Comparator.NE:
        ok = left != right
    elif cmp == Comparator.GE:
        ok = left >= right
    elif cmp == Comparator.GT:
        ok = left > right
    elif cmp == Comparator.WITHIN_TOL:
        ok = abs(left - right) <= (criterion.tolerance or 0.0)
    else:  # pragma: no cover — enum exhaustive
        return SatisfactionVerdict.UNDETERMINED
    return SatisfactionVerdict.SATISFIED if ok else SatisfactionVerdict.REFUTED


def evaluate(
    plan: EvaluationPlan,
    ctx: MaterializationContext,
    adapter: Adapter,
    *,
    claim_leaves: tuple[Leaf, ...] = (),
) -> EvaluationResult:
    """Execute `plan` with ONE adapter. Pure; never raises on a node error."""
    graph = plan.graph
    node_by_id = {n.id: n for n in graph.nodes}
    outputs: dict[str, ExecValue] = {}
    node_evals: list[NodeEvaluation] = []
    had_error = False

    for nid in graph.topological_order:
        node = node_by_id[nid]
        upstream = tuple(
            outputs.get(inp.node_id, ExecValue(value=None))
            for inp in node.inputs
            if isinstance(inp, NodeRef)
        )
        error: str | None = None
        try:
            out = adapter.execute(node, upstream, ctx)
        except Exception as exc:  # noqa: BLE001 — runtime degrades, never crashes
            out = ExecValue(value=None)
            error = f"{type(exc).__name__}: {exc}"
            had_error = True
        outputs[nid] = out
        node_evals.append(
            NodeEvaluation(
                node_id=nid,
                impl=node.impl,
                produced=None if error else _wrap_leaf(node.produces, out.value),
                drift=_drift(_params(node).get("expected"), out.value),
                error=error,
            )
        )

    terminal = outputs[graph.terminal]
    verdict = _apply_criterion(plan.criterion, terminal, claim_leaves)
    if not had_error:
        status: Literal["complete", "partial", "error"] = "complete"
    elif terminal.value is not None:
        status = "partial"
    else:
        status = "error"
    return EvaluationResult(
        verdict=verdict,
        terminal=terminal,
        nodes=tuple(node_evals),
        adapter_identity=adapter.identity,
        status=status,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_evaluate.py -q`
Expected: PASS (13 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/evaluate.py grammar/tests/test_evaluate.py
git commit -m "feat(grammar): evaluate() runtime — topo exec, typed-leaf wrap, 3-valued criterion, drift"
```

---

## Task 7: `evaluate.py` — `verify()` air-gap gate + exports

**Files:**
- Modify: `grammar/src/polymer_grammar/evaluate.py` (append `_check_agreement` + `verify`)
- Modify: `grammar/src/polymer_grammar/__init__.py` (export evaluate API)
- Test: `grammar/tests/test_evaluate.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# append to grammar/tests/test_evaluate.py
from polymer_grammar.evaluate import verify
import pytest


def test_verify_mints_satisfaction_on_agreement():
    ve = verify(_plan(), _ctx(), (IdentityAdapter(), ReferenceAdapter()))
    assert ve.agreement is True
    assert ve.satisfaction is not None
    assert ve.satisfaction.verdict == SatisfactionVerdict.SATISFIED
    assert ve.satisfaction.materialization.id == "m1"


def test_verify_rejects_single_adapter():
    with pytest.raises(SelfLicensingError):
        verify(_plan(), _ctx(), (IdentityAdapter(),))


def test_verify_rejects_same_identity_pair():
    with pytest.raises(SelfLicensingError):
        verify(_plan(), _ctx(), (IdentityAdapter(), IdentityAdapter()))


def test_verify_no_satisfaction_on_value_disagreement():
    ve = verify(_plan(), _ctx(), (IdentityAdapter(), ReferenceAdapter(perturb=1.0)))
    assert ve.agreement is False
    assert ve.satisfaction is None
    assert ve.disagreement is not None


def test_verify_no_satisfaction_when_agreed_but_refuted():
    ve = verify(
        _plan(params=(("value", "0.9"),)),
        _ctx(),
        (IdentityAdapter(), ReferenceAdapter()),
    )
    assert ve.agreement is True
    assert ve.satisfaction is None  # agreed verdict is REFUTED, not SATISFIED


def test_evaluate_public_api_is_exported():
    import polymer_grammar as pg

    for name in (
        "evaluate", "verify", "Adapter", "ExecValue", "EvaluationResult",
        "VerifiedEvaluation", "NodeEvaluation", "Drift", "IdentityAdapter",
        "ReferenceAdapter", "SelfLicensingError",
    ):
        assert hasattr(pg, name), name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd grammar && uv run pytest tests/test_evaluate.py -q`
Expected: FAIL — `ImportError: cannot import name 'verify'`

- [ ] **Step 3: Write minimal implementation**

Append to `grammar/src/polymer_grammar/evaluate.py`:

```python
def _check_agreement(
    results: tuple[EvaluationResult, ...], abs_tol: float, rel_tol: float
) -> tuple[bool, str | None]:
    verdicts = {r.verdict for r in results}
    if len(verdicts) > 1:
        return False, f"verdict disagreement: {sorted(v.value for v in verdicts)}"
    vals = [r.terminal.value for r in results]
    numeric = [v for v in vals if isinstance(v, (int, float))]
    if len(numeric) == len(vals) and numeric:
        lo, hi = min(numeric), max(numeric)
        ad = abs(hi - lo)
        denom = max(abs(hi), abs(lo), 1.0)
        if ad > abs_tol and ad / denom > rel_tol:
            return False, f"terminal value disagreement: {vals}"
        return True, None
    if len(set(vals)) > 1:
        return False, f"terminal value disagreement: {vals}"
    return True, None


def verify(
    plan: EvaluationPlan,
    ctx: MaterializationContext,
    adapters: tuple[Adapter, ...],
    *,
    claim_leaves: tuple[Leaf, ...] = (),
    agreement_abs_tol: float = _ABS_TOL,
    agreement_rel_tol: float = _REL_TOL,
) -> VerifiedEvaluation:
    """Run `plan` under >=2 distinct-identity adapters; mint a Satisfaction ONLY on
    agreement + SATISFIED. The structural 'no self-licensing' air-gap."""
    if len(adapters) < 2:
        raise SelfLicensingError("verify requires >= 2 adapters (writer != verifier)")
    identities = {a.identity for a in adapters}
    if len(identities) < 2:
        raise SelfLicensingError(
            "verify requires >= 2 DISTINCT adapter identities (air-gap: writer != "
            f"verifier); got {sorted(identities)}"
        )
    results = tuple(
        evaluate(plan, ctx, a, claim_leaves=claim_leaves) for a in adapters
    )
    agreement, detail = _check_agreement(results, agreement_abs_tol, agreement_rel_tol)
    satisfaction: Satisfaction | None = None
    if agreement and results[0].verdict == SatisfactionVerdict.SATISFIED:
        satisfaction = Satisfaction(
            verdict=SatisfactionVerdict.SATISFIED, materialization=ctx
        )
    return VerifiedEvaluation(
        results=results,
        agreement=agreement,
        satisfaction=satisfaction,
        disagreement=detail,
    )
```

In `grammar/src/polymer_grammar/__init__.py`, add the import block (after the `.operations` import) and extend `__all__`:

```python
from .evaluate import (
    Adapter,
    Drift,
    EvaluationResult,
    ExecValue,
    IdentityAdapter,
    NodeEvaluation,
    ReferenceAdapter,
    SelfLicensingError,
    VerifiedEvaluation,
    evaluate,
    verify,
)
```
Add to `__all__`:
```python
    "Adapter",
    "Drift",
    "EvaluationResult",
    "ExecValue",
    "IdentityAdapter",
    "NodeEvaluation",
    "ReferenceAdapter",
    "SelfLicensingError",
    "VerifiedEvaluation",
    "evaluate",
    "verify",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd grammar && uv run pytest tests/test_evaluate.py -q`
Expected: PASS (19 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add grammar/src/polymer_grammar/evaluate.py grammar/src/polymer_grammar/__init__.py grammar/tests/test_evaluate.py
git commit -m "feat(grammar): verify() air-gap gate — distinct-identity + agreement -> mint Satisfaction"
```

---

## Task 8: Full-suite green, lint, isolation, docs

**Files:**
- Modify: `docs/superpowers/CONTINUE.md`
- Modify: `docs/superpowers/plans/2026-06-02-evaluator.md` (this file — Progress Log)

- [ ] **Step 1: Run the whole suite**

Run: `cd grammar && uv run pytest -q`
Expected: PASS — all prior tests (189) + the new operations/claim/evaluate tests, 0 failures.

- [ ] **Step 2: Lint**

Run: `cd grammar && uv run ruff check src tests`
Expected: `All checks passed!` (fix any reported issues — typically unused imports or line length — then re-run).

- [ ] **Step 3: Confirm isolation still holds**

Run: `cd grammar && uv run pytest tests/test_isolation.py -q`
Expected: PASS — `evaluate.py`/`operations.py` import nothing from `polymer_formalclaim` and no infra.

- [ ] **Step 4: Update CONTINUE.md**

In `docs/superpowers/CONTINUE.md`, update the "Current state" line and the "NEXT" section to record Phase 8 done: operations IR + evaluator (`operations.py`, `evaluate.py`) shipped; the air-gap two-implementation verifier mints L2 `Satisfaction`s; requirement #2 (oracle) now unblocked via `OperationNode.oracle_ref`. Note the new test count. Set NEXT to the oracle dossier (#2) / protocol runtime per the spec's §7 fence.

- [ ] **Step 5: Update this plan's Progress Log + commit**

Add a `## Progress Log` section at the bottom of this file with one line per task (commit hash + any decisions), per the user's standing habit.

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add docs/superpowers/CONTINUE.md docs/superpowers/plans/2026-06-02-evaluator.md
git commit -m "docs: Phase 8 evaluator complete — update CONTINUE + plan progress log"
```

---

## Self-Review (completed by plan author)

**Spec coverage** (spec §3–§8 → task):
- §3.1 DataHandle, §3.2 NodeRef/OpInput, §3.3 ProducedLeafSpec, §3.4 OperationNode → Task 1.
- §3.5 ComputeGraph (unique/acyclic/resolvable + topo + content_hash) → Task 2.
- §3.6 SatisfactionCriterion, §3.7 EvaluationPlan → Task 3.
- §3.8 Claim.evaluation_plan wiring → Task 4.
- §4.1 Adapter Protocol + ExecValue + reference adapters, §5 result models → Task 5.
- §4.2 evaluate() (topo, typed wrap, 3-valued criterion, drift, dimension check) → Task 6.
- §4.3 verify() air-gap (distinct identity, agreement, mint Satisfaction) → Task 7.
- §8 testing (full suite + isolation + ruff) → Task 8.
- §7 scope fence: nothing in the plan builds real adapters, the oracle dossier, full UCUM algebra, Licensing/Status assembly, or the representation_revision tier. `oracle_ref` is a declared-but-unbound slot only (Task 1). ✓

**Placeholder scan:** every code step shows complete code; no TBD/TODO/"add validation". ✓

**Type consistency:** `ExecValue.value: float | str | None`, `Adapter.execute(node, upstream, ctx)`, and `evaluate(..., claim_leaves=())` signatures match across Tasks 5–7. `verify` returns `VerifiedEvaluation` with the `satisfaction`/`agreement`/`disagreement` fields the Task-7 tests assert. `_params` is defined in Task 5 and reused in Task 6. The `expected` drift param and the `builtin::*` impl names are consistent between adapter handlers (Task 5) and the evaluate tests (Task 6). ✓

**One implementation-note for the executing engineer:** the `evaluate()` step adds several imports to `evaluate.py`'s existing import block — merge them with the imports written in Task 5 rather than duplicating the `from .leaf import ...` / `from .operations import ...` lines (ruff will flag a redefinition otherwise).

---

## Progress Log

Executed subagent-driven (fresh implementer + spec-compliance review + code-quality review per task; final whole-package Opus review). All on branch `phase8-evaluator`, merged no-ff to `main`. Final state: **240 tests green, ruff clean, isolation holds.**

- **Task 1 — operations IR primitives** (`0ce7d69`). DataHandle/NodeRef/OpInput/ProducedLeafSpec/OperationNode. Review fixes: `_sha` scaffolding comment; strengthened NodeRef test.
- **Task 2 — ComputeGraph** (`b84352f`). Validators (unique/acyclic/resolvable) + topo + content_hash. Review fixes: `content_hash` uses `model_dump(mode="json")` (future-field-proof); pinned-hash + diamond-topo tests added.
- **Task 3 — SatisfactionCriterion + EvaluationPlan** (`8a1faa5`). Review tightening: reject `tolerance` on non-WITHIN_TOL comparators (stricter than spec; with test); clarifying comment on the exactly-one idiom.
- **Task 4 — Claim.evaluation_plan + exports** (`c628f84`). Additive-optional field + 9 operations symbols exported. Review fix: added `OpInput` to the export-completeness test.
- **Task 5 — evaluate.py models + adapters** (`2f13968`). Result models, Adapter Protocol, two reference adapters. Review fixes: ReferenceAdapter propagates dimension on `builtin::identity`; fmean/sum precision comment; adapter error-contract docstring; `builtin::identity` tests; strengthened the existence-error test.
- **Task 6 — evaluate() runtime** (`cefc482`). **CRITICAL fix in review:** `_wrap_leaf` was outside the try/except → an adapter returning a non-numeric value for a quantity node crashed `evaluate()`, violating "never raises"; now guarded + node degrades to error. **IMPORTANT fix:** mixed str/numeric comparison returned wrong verdicts → now UNDETERMINED. Plus strict existence wrapping + partial-status / multi-node-chain / drift-out-of-tolerance / string-comparison tests. Re-reviewed and confirmed.
- **Task 7 — verify() air-gap gate + exports** (`3755960`). ≥2-distinct-identity gate → mint Satisfaction only on agreement + SATISFIED. Review fixes: documented identity-string distinctness as necessary-not-sufficient (registry's job); UNDETERMINED-agreement test; agreement-semantics comments.
- **Task 8 — finalize** (this commit). Full suite + ruff + isolation green; final Opus whole-package review = READY TO MERGE; stale module docstring cleaned; CONTINUE + this log updated.
