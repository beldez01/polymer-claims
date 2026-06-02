"""evaluate.py — the v1.3 evaluator runtime (Phase 8; spec §4).

The "runtime" half of the compiler/runtime split: executes a claim's EvaluationPlan
(operations.py) against a MaterializationContext and PRODUCES the L2 Satisfaction that the
static Licensing record consumes — but only through an air-gapped, two-implementation
agreement gate (`verify`, a later task), so a claim can never license itself. Pure +
adapter-injected; imports NO infra (no network/R/scipy). Real adapters live OUTSIDE this
package; the reference adapters here are deterministic and exist to exercise the plumbing +
the air-gap. This task ships the result models, the Adapter Protocol, and reference adapters;
`evaluate()` / `verify()` land in later tasks.
"""
from __future__ import annotations

import statistics
from typing import Literal, Protocol

from .base import _Model
from .leaf import Leaf
from .licensing import MaterializationContext, Satisfaction, SatisfactionVerdict
from .operations import OperationNode
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
    ) -> ExecValue:
        """Execute a single operation node and return its produced value.

        Receives the node, the already-executed ExecValues of the node's NodeRef inputs
        (in input order), and the materialization context. Resolving DataHandle inputs is
        the adapter's own responsibility. The adapter MAY raise on a bad impl/inputs; the
        evaluator (a later task) catches the exception and degrades that node to an error
        (it does not crash the run).
        """
        ...


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
        if node.impl == "builtin::const":
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
        dim = None
        if node.impl == "builtin::const":
            out: float | str | None = float(p["value"])
        elif node.impl == "builtin::identity":
            if upstream:
                base = upstream[0].value
                out = float(base) if isinstance(base, (int, float)) else base
                dim = upstream[0].dimension
            else:
                out = float(p["value"])
        elif node.impl == "builtin::mean":
            # fmean uses math.fsum (exact) vs IdentityAdapter's naive sum/len — a deliberate
            # second implementation. Cross-adapter agreement must compare value-within-tolerance,
            # not exact float equality (the two can diverge on cancellation-heavy vectors).
            out = statistics.fmean(float(x) for x in p["vector"].split(","))
        else:
            raise ValueError(f"ReferenceAdapter has no handler for impl {node.impl!r}")
        if self.perturb and isinstance(out, (int, float)):
            out = float(out) + self.perturb
        return ExecValue(value=out, dimension=dim)
