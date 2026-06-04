"""Shared fixtures: minimal claims, evaluation plans, adapters, and corpora."""
from __future__ import annotations

import pytest
from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    EvaluationPlan,
    FDRLedger,
    IdentityAdapter,
    MaterializationContext,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    ReferenceAdapter,
    SatisfactionCriterion,
    Status,
    StrengthVector,
)

from polymer_protocol.corpus import Corpus

_PATTERN = PatternRef(id="adjusted_effect", version="v1")


def make_claim(
    cid: str,
    status: Status = Status.CONJECTURED,
    *,
    plan: EvaluationPlan | None = None,
    pending_reason: PendingReason | None = None,
    strength: StrengthVector | None = None,
    pattern: PatternRef | None = None,
    **extra,
) -> Claim:
    if status == Status.PENDING and pending_reason is None:
        pending_reason = PendingReason.UNTESTED
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=pattern or _PATTERN,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=status,
        pending_reason=pending_reason,
        strength=strength,
        evaluation_plan=plan,
        **extra,
    )


def make_plan(
    value: float, threshold: float, comparator: Comparator = Comparator.LT,
    *, oracle_ref: str | None = None,
) -> EvaluationPlan:
    """A one-node plan: a constant `value`, tested against `threshold`. `oracle_ref` lets a
    test attach an oracle to the node (still impl=builtin::const, so the reference adapters
    execute it)."""
    node = OperationNode(
        id="n0",
        impl="builtin::const",
        params=(("value", str(value)),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
        oracle_ref=oracle_ref,
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
    )


@pytest.fixture
def ctx() -> MaterializationContext:
    return MaterializationContext(id="M1", api_version="v1", data_version="d1")


@pytest.fixture
def adapters() -> tuple:
    """Two distinct-identity reference adapters — satisfies verify()'s air-gap."""
    return (IdentityAdapter(), ReferenceAdapter(identity="reference"))


@pytest.fixture
def empty_ledger() -> FDRLedger:
    return FDRLedger(target_fdr=0.05)


@pytest.fixture
def empty_corpus(empty_ledger) -> Corpus:
    return Corpus(fdr_ledger=empty_ledger)
