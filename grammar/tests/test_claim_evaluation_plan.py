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
        "DataHandle", "NodeRef", "OpInput", "OperationNode", "ProducedLeafSpec",
        "ComputeGraph", "Comparator", "SatisfactionCriterion", "EvaluationPlan",
    ):
        assert hasattr(pg, name), name
