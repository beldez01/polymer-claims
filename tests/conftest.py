"""Umbrella-test fixtures — minimal claim/corpus builders mirroring
`protocol/tests/conftest.py` (kept local so the umbrella tests don't depend on the
protocol package's test tree)."""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    EvaluationPlan,
    FDRLedger,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    SatisfactionCriterion,
    Status,
)
from polymer_protocol import Corpus

_PATTERN = PatternRef(id="adjusted_effect", version="v1")


def make_plan(
    value: float, threshold: float, comparator: Comparator = Comparator.LT
) -> EvaluationPlan:
    node = OperationNode(
        id="n0",
        impl="builtin::const",
        params=(("value", str(value)),),
        produces=ProducedLeafSpec(
            leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED
        ),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
    )


def make_claim(
    cid: str,
    status: Status = Status.CONJECTURED,
    *,
    plan: EvaluationPlan | None = None,
) -> Claim:
    pending_reason = PendingReason.UNTESTED if status == Status.PENDING else None
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=status,
        pending_reason=pending_reason,
        evaluation_plan=plan,
    )


def licensing_corpus() -> Corpus:
    """A one-claim corpus whose PENDING claim licenses on a single run_cycle."""
    claim = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
