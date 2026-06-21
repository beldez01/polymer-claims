"""Shared fixtures: minimal claims, evaluation plans, adapters, and corpora."""
from __future__ import annotations

import pytest
from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    Dimension,
    EvaluationPlan,
    FDRLedger,
    IdentityAdapter,
    MaterializationContext,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    QuantityLeaf,
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


def make_quantity_claim(
    cid: str,
    value: float,
    status: Status = Status.LICENSED,
    *,
    dim: tuple[tuple[str, int], ...] | None = (),
    unit: str | None = None,
    pending_reason: PendingReason | None = None,
    pattern: PatternRef | None = None,
) -> Claim:
    """Build a minimal valid Claim with one QuantityLeaf for sheaf tests.

    ``dim`` is the raw exponents tuple for Dimension (or None for no dimension).
    ``unit`` is only valid for FUNDAMENTAL basis; use None for DERIVED (formula required).
    """
    if status == Status.PENDING and pending_reason is None:
        pending_reason = PendingReason.UNTESTED
    dimension = Dimension(exponents=dim) if dim is not None else None
    if unit is not None:
        # FUNDAMENTAL basis allows a unit; no formula needed
        leaf = QuantityLeaf(
            value=value,
            unit=unit,
            measurement_basis=MeasurementBasis.FUNDAMENTAL,
            dimension=dimension,
        )
    else:
        # DERIVED basis: no unit, formula required
        leaf = QuantityLeaf(
            value=value,
            measurement_basis=MeasurementBasis.DERIVED,
            formula="test::const",
            dimension=dimension,
        )
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=pattern or _PATTERN,
        leaves=(leaf,),
        status=status,
        pending_reason=pending_reason,
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
