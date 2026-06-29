"""operations.py — the v1.3 operations IR (Phase 8; spec 2026-06-02-evaluator-spec.md §3).

A typed compute DAG: the declarative ("compiler-side") half of the compiler/runtime split —
HOW a claim is checked against data, expressed as DATA, not code. Each OperationNode names a
versioned `impl` dispatch key plus typed inputs (DataHandles into a materialization, or
NodeRefs to upstream outputs) and declares the TYPE of L0 Leaf it produces. The graph
terminates in a SatisfactionCriterion (later task) that turns the terminal output into a
3-valued verdict. The runtime that EXECUTES this lives in evaluate.py; this module ships only
the frozen, content-addressed type. Imports nothing from polymer_protocol/polymer_claims and no infra.
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import Field, model_serializer, model_validator

from .base import _Model
from .leaf import MeasurementBasis
from .units import Dimension


# content-addressing helper; consumed by ComputeGraph.content_hash (next task)
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
    def _basis_discipline(self) -> ProducedLeafSpec:
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


class ComputeGraph(_Model):
    nodes: tuple[OperationNode, ...] = Field(min_length=1)
    terminal: str = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> ComputeGraph:
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"OperationNode ids must be unique; duplicates: {dupes}")
        return self

    @model_validator(mode="after")
    def _refs_resolve(self) -> ComputeGraph:
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
    def _acyclic(self) -> ComputeGraph:
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
            (n.model_dump(mode="json") for n in self.nodes),
            key=lambda d: d["id"],
        )
        return _sha({"terminal": self.terminal, "nodes": node_dicts})


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
    def _exactly_one_target(self) -> SatisfactionCriterion:
        has_thr = self.threshold is not None
        has_ref = self.reference_leaf_index is not None
        if has_thr == has_ref:  # both set (True==True) or neither (False==False)
            raise ValueError(
                "SatisfactionCriterion requires exactly one of `threshold` or "
                "`reference_leaf_index`"
            )
        return self

    @model_validator(mode="after")
    def _tolerance_iff_within_tol(self) -> SatisfactionCriterion:
        if self.comparator == Comparator.WITHIN_TOL and self.tolerance is None:
            raise ValueError("comparator=within_tol requires a `tolerance`")
        if self.comparator != Comparator.WITHIN_TOL and self.tolerance is not None:
            raise ValueError(
                f"`tolerance` is only valid with comparator=within_tol; "
                f"got comparator={self.comparator.value}"
            )
        return self


class EvaluationPlan(_Model):
    graph: ComputeGraph
    criterion: SatisfactionCriterion
    # V2.0: optional execution contract; omitted from serialized output when None
    # (so existing plans' model_dump_json / commitment_hash stay byte-identical).
    execution_contract: ExecutionContract | None = None

    @model_serializer(mode="wrap")
    def _serialize(self, handler) -> dict:
        """Drop execution_contract from the output when None so existing plans'
        model_dump/model_dump_json stays byte-identical (no new key)."""
        data = handler(self)
        if data.get("execution_contract") is None:
            data.pop("execution_contract", None)
        return data


# Late import to break the circular dependency: verification_policy.py imports
# LicenseRoute / MaterializationContext from licensing.py, which in turn late-imports
# EvidenceProvenance from verification_policy.py. Importing ExecutionContract here
# (after EvaluationPlan is defined) mirrors the Task 8/9 pattern in licensing.py and
# capability.py. model_rebuild() completes the EvaluationPlan schema with the resolved type.
from .verification_policy import ExecutionContract  # noqa: E402
EvaluationPlan.model_rebuild()
