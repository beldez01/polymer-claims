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
from .leaf import (
    CategoricalLeaf,
    ExistenceLeaf,
    Leaf,
    MeasurementBasis,
    PropositionLeaf,
    QuantityLeaf,
)
from .licensing import MaterializationContext, Satisfaction, SatisfactionVerdict
from .operations import (
    Comparator,
    EvaluationPlan,
    NodeRef,
    OperationNode,
    SatisfactionCriterion,
)
from .units import Dimension, compatible


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
        # invalid state -> ValidationError, caught by evaluate()'s wrap guard
        return ExistenceLeaf(state=value)  # type: ignore[arg-type]
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
    if isinstance(lhs, str) != isinstance(rhs, str):
        return SatisfactionVerdict.UNDETERMINED
    if isinstance(lhs, str) or isinstance(rhs, str):  # both str here
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
        ok = left == right  # exact equality — use WITHIN_TOL for computed reals (float rounding)
    elif cmp == Comparator.NE:
        ok = left != right
    elif cmp == Comparator.GE:
        ok = left >= right
    elif cmp == Comparator.GT:
        ok = left > right
    elif cmp == Comparator.WITHIN_TOL:
        ok = abs(left - right) <= (criterion.tolerance or 0.0)  # tolerance is guaranteed non-None for WITHIN_TOL by the SatisfactionCriterion validator
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
        produced = None
        if error is None:
            try:
                produced = _wrap_leaf(node.produces, out.value)
            except Exception as exc:  # noqa: BLE001 — bad adapter output degrades the node
                error = f"{type(exc).__name__}: {exc}"
                had_error = True
                out = ExecValue(value=None)
        # Promote declared produces.dimension into ExecValue when adapter didn't set one.
        if out.dimension is None and node.produces.dimension is not None and out.value is not None:
            out = ExecValue(value=out.value, dimension=node.produces.dimension)
        outputs[nid] = out
        node_evals.append(
            NodeEvaluation(
                node_id=nid,
                impl=node.impl,
                produced=produced,
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
        denom = max(abs(hi), abs(lo), 1.0)  # 1.0 floor avoids div-by-zero and over-tight relative checks near zero
        if ad > abs_tol and ad / denom > rel_tol:
            return False, f"terminal value disagreement: {vals}"
        return True, None
    if len(set(vals)) > 1:
        return False, f"terminal value disagreement: {vals}"
    # equal non-numeric values agree (incl. both-None); minting is still gated on SATISFIED in verify()
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
    agreement + SATISFIED. The structural 'no self-licensing' air-gap: the writer of a
    claim must not also be its verifier, so >=2 DISTINCT adapter identities are required.

    Identity-string uniqueness is necessary but not sufficient: ensuring that distinct
    identities map to genuinely independent implementations (so a single actor cannot
    supply two cosmetically-different adapters) is the responsibility of the adapter
    registry / protocol layer, not this function.
    """
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
