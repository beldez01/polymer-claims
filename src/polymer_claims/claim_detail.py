"""Pure display-card builder for a single `Claim`.

The live node server streams only a thin topology projection of each claim. This
module derives a richer, JSON-serializable "card" the viewer can show in a
detail panel — including a best-effort rejection reason inferred from the claim's
`builtin::const` evaluation plan (the only plan shape the umbrella generators
currently emit).

Dependency-light by design: imports only from `polymer_grammar`. NOTHING here
imports fastapi/anthropic, so it stays on the core (extra-free) import graph.
"""
from __future__ import annotations

from typing import Any

from polymer_grammar import Comparator, Status

# StrengthVector axis order for the emitted 6-tuple.
_STRENGTH_AXES = (
    "magnitude",
    "certainty",
    "evidence_against_null",
    "severity",
    "world_contact",
    "explanatory_virtue",
)

_CONST_IMPL = "builtin::const"


def _terminal_node(claim: Any) -> Any | None:
    """Return the plan's terminal OperationNode, or None if there's no plan."""
    plan = claim.evaluation_plan
    if plan is None:
        return None
    graph = plan.graph
    return next((n for n in graph.nodes if n.id == graph.terminal), None)


def _const_value(node: Any) -> float | None:
    """Read the `value` param of a `builtin::const` node as a float, else None."""
    if node is None or node.impl != _CONST_IMPL:
        return None
    for key, val in node.params:
        if key == "value":
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
    return None


def _compare(value: float, comparator: Comparator, threshold: float, tolerance: float | None) -> bool:
    """Const-vs-threshold satisfaction, matching grammar's `evaluate` semantics."""
    if comparator == Comparator.LT:
        return value < threshold
    if comparator == Comparator.LE:
        return value <= threshold
    if comparator == Comparator.EQ:
        return value == threshold
    if comparator == Comparator.NE:
        return value != threshold
    if comparator == Comparator.GE:
        return value >= threshold
    if comparator == Comparator.GT:
        return value > threshold
    if comparator == Comparator.WITHIN_TOL:
        return abs(value - threshold) <= (tolerance or 0.0)
    return False  # pragma: no cover — enum exhaustive


def _const_eval(claim: Any) -> tuple[float, Comparator, float, float | None] | None:
    """Extract (value, comparator, threshold, tolerance) for a const plan with a
    threshold-based criterion, else None. Shared by both public functions so they
    agree on what's evaluable."""
    plan = claim.evaluation_plan
    if plan is None:
        return None
    node = _terminal_node(claim)
    value = _const_value(node)
    if value is None:
        return None
    criterion = plan.criterion
    if criterion.threshold is None:
        return None
    return value, criterion.comparator, criterion.threshold, criterion.tolerance


def derive_rejection_reason(claim: Any) -> str | None:
    """Best-effort human-readable rejection reason.

    Only REJECTED claims get a non-None reason. For a const plan we report
    whether the criterion was met (rejected despite passing → likely defeated /
    duplicate / significance bar) or not (criterion not met). Claims without an
    evaluable const criterion get a generic rejected note.
    """
    if claim.status != Status.REJECTED:
        return None
    extracted = _const_eval(claim)
    if extracted is None:
        return "rejected — no const criterion to evaluate (likely defeated or significance bar)"
    value, comparator, threshold, tolerance = extracted
    satisfied = _compare(value, comparator, threshold, tolerance)
    if satisfied:
        return (
            "criterion met but rejected — likely defeated by a rival, a duplicate, "
            "or the selective-significance bar"
        )
    return f"criterion not met — const({value:g}) {comparator.value} {threshold:g} is FALSE"


def claim_detail(claim: Any) -> dict[str, Any]:
    """Build a JSON-serializable display card for one claim."""
    # subject_term: first leaf carrying a non-empty ontology_term.
    subject_term: str | None = None
    for leaf in claim.leaves:
        term = getattr(leaf, "ontology_term", None)
        if isinstance(term, str) and term:
            subject_term = term
            break

    plan = claim.evaluation_plan
    plan_dict: dict[str, Any] | None = None
    criterion_dict: dict[str, Any] | None = None
    if plan is not None:
        terminal = _terminal_node(claim)
        if terminal is not None and terminal.impl == _CONST_IMPL:
            value = _const_value(terminal)
            plan_dict = {"impl": _CONST_IMPL, "value": value}
        elif terminal is not None:
            plan_dict = {"impl": terminal.impl}
        criterion = plan.criterion
        criterion_dict = {
            "comparator": criterion.comparator.value,
            "threshold": criterion.threshold,
            "tolerance": criterion.tolerance,
        }

    # criterion_satisfied: only for an evaluable const plan WITH a criterion.
    criterion_satisfied: bool | None = None
    extracted = _const_eval(claim)
    if extracted is not None:
        value, comparator, threshold, tolerance = extracted
        criterion_satisfied = _compare(value, comparator, threshold, tolerance)

    strength: list[float] | None = None
    if claim.strength is not None:
        strength = [float(getattr(claim.strength, axis)) for axis in _STRENGTH_AXES]

    provenance: dict[str, Any] | None = None
    if claim.provenance is not None:
        provenance = {
            "generated_by": claim.provenance.generated_by.value,
            "agent_id": claim.provenance.agent_id,
            "method": claim.provenance.method,
        }

    return {
        "id": claim.id,
        "title": claim.title,
        "status": claim.status.value,
        "pattern_id": claim.pattern.id,
        "subject_term": subject_term,
        "plan": plan_dict,
        "criterion": criterion_dict,
        "criterion_satisfied": criterion_satisfied,
        "strength": strength,
        "provenance": provenance,
        "rejection_reason": derive_rejection_reason(claim),
    }
