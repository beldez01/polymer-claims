"""Pure plan synthesis for executable-generation (#4b slice-2, spec §3.1).

A rival of a planned claim tests the SAME data through the SAME computation, expecting the
opposite result. mirror_criterion flips a criterion to its logical complement at the same
boundary; transplant_plan reuses the source graph verbatim with that mirrored criterion, so
source + rival co-evaluate (exactly one SATISFIED on one data realization). None when the
criterion's comparator has no single-Comparator complement (WITHIN_TOL). Deterministic, pure.
"""
from __future__ import annotations

from polymer_grammar import Comparator, EvaluationPlan, SatisfactionCriterion

_MIRROR: dict[Comparator, Comparator] = {
    Comparator.LT: Comparator.GE,
    Comparator.GE: Comparator.LT,
    Comparator.LE: Comparator.GT,
    Comparator.GT: Comparator.LE,
    Comparator.EQ: Comparator.NE,
    Comparator.NE: Comparator.EQ,
}


def mirror_criterion(criterion: SatisfactionCriterion) -> SatisfactionCriterion | None:
    """The logical complement of `criterion` at the SAME boundary (same threshold/reference),
    so on identical data exactly one of {criterion, mirror} is SATISFIED. None for WITHIN_TOL."""
    flipped = _MIRROR.get(criterion.comparator)
    if flipped is None:
        return None
    return criterion.model_copy(update={"comparator": flipped})


def transplant_plan(plan: EvaluationPlan) -> EvaluationPlan | None:
    """Reuse the source graph VERBATIM with a mirrored criterion; None when not mirrorable."""
    mirrored = mirror_criterion(plan.criterion)
    if mirrored is None:
        return None
    return plan.model_copy(update={"criterion": mirrored})
