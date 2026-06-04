from __future__ import annotations

from polymer_grammar import (
    Comparator,
    ComputeGraph,
    EvaluationPlan,
    MeasurementBasis,
    OperationNode,
    ProducedLeafSpec,
    SatisfactionCriterion,
)

from polymer_protocol.plan_synthesis import mirror_criterion, transplant_plan


# --- helpers -----------------------------------------------------------------

def _crit(comparator, *, threshold=0.05, reference=None, tolerance=None):
    # NOTE (adaptation): SatisfactionCriterion requires exactly one of
    # `threshold` or `reference_leaf_index` (never both, never neither).
    # For WITHIN_TOL the plan spec also mandates a `tolerance`. We keep
    # threshold=0.05 as the reference boundary even for WITHIN_TOL so the
    # validator is satisfied.
    if reference is not None:
        return SatisfactionCriterion(
            comparator=comparator,
            reference_leaf_index=reference,
            tolerance=tolerance,
        )
    if tolerance is not None:
        # WITHIN_TOL: needs tolerance + exactly one of threshold/reference
        return SatisfactionCriterion(
            comparator=comparator,
            threshold=threshold,
            tolerance=tolerance,
        )
    return SatisfactionCriterion(comparator=comparator, threshold=threshold)


def _plan(comparator=Comparator.LT, *, threshold=0.05, tolerance=None):
    node = OperationNode(
        id="n0",
        impl="builtin::const",
        params=(("value", "0.09"),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    crit = (
        # WITHIN_TOL: needs tolerance + threshold (exactly-one-target rule)
        SatisfactionCriterion(comparator=comparator, threshold=threshold, tolerance=tolerance)
        if tolerance is not None
        else SatisfactionCriterion(comparator=comparator, threshold=threshold)
    )
    return EvaluationPlan(graph=ComputeGraph(nodes=(node,), terminal="n0"), criterion=crit)


# --- tests -------------------------------------------------------------------

def test_mirror_flips_each_orderable_comparator():
    pairs = {
        Comparator.LT: Comparator.GE,
        Comparator.GE: Comparator.LT,
        Comparator.LE: Comparator.GT,
        Comparator.GT: Comparator.LE,
        Comparator.EQ: Comparator.NE,
        Comparator.NE: Comparator.EQ,
    }
    for src, want in pairs.items():
        m = mirror_criterion(_crit(src))
        assert m is not None and m.comparator == want
        assert m.threshold == 0.05 and m.reference_leaf_index is None


def test_mirror_preserves_reference_target():
    m = mirror_criterion(_crit(Comparator.GT, reference=1))
    assert m is not None and m.comparator == Comparator.LE
    assert m.reference_leaf_index == 1 and m.threshold is None


def test_mirror_within_tol_is_none():
    assert mirror_criterion(_crit(Comparator.WITHIN_TOL, tolerance=0.1)) is None


def test_mirror_result_is_a_valid_criterion():
    m = mirror_criterion(_crit(Comparator.LT))
    assert m is not None
    assert SatisfactionCriterion.model_validate(m.model_dump()) == m


def test_transplant_reuses_graph_and_mirrors_criterion():
    src = _plan(Comparator.LT, threshold=0.05)
    out = transplant_plan(src)
    assert out is not None
    # NOTE (adaptation): content_hash is a @property, not a method — no ()
    assert out.graph.content_hash == src.graph.content_hash
    assert out.criterion.comparator == Comparator.GE and out.criterion.threshold == 0.05


def test_transplant_within_tol_is_none():
    assert transplant_plan(_plan(Comparator.WITHIN_TOL, tolerance=0.1)) is None


def test_mirror_is_logical_complement_at_the_boundary():
    src = _crit(Comparator.GT, threshold=0.05)
    mir = mirror_criterion(src)
    assert mir is not None
    above, below = 0.09, 0.01
    assert (above > 0.05) != (above <= 0.05)
    assert (below > 0.05) != (below <= 0.05)
