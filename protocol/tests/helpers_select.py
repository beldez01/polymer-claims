"""Shared fixture builders for select-stage tests that need DataHandle-bearing plans."""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    ComputeGraph,
    Comparator,
    DataHandle,
    EvaluationPlan,
    FDRLedger,
    GenerationMode,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    Provenance,
    SatisfactionCriterion,
    Status,
    StrengthVector,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.cost import CostModel, CostVector, CostWeights

_PATTERN = PatternRef(id="adjusted_effect", version="v1")

# A CostModel that resolves every claim to wall_latency=1.0.
SIMPLE_COST = CostModel(default=CostVector(wall_latency=1.0))
SIMPLE_COST_WEIGHTS = CostWeights()


def _make_plan_with_data_handle(ref: str) -> EvaluationPlan:
    """One-node plan whose single input is a DataHandle(ref=ref)."""
    node = OperationNode(
        id="n0",
        impl="builtin::const",
        inputs=(DataHandle(ref=ref),),
        params=(("value", "0.01"),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
    )


def _make_sv() -> StrengthVector:
    """A fixed StrengthVector so both candidates have identical value vectors."""
    return StrengthVector(
        magnitude=0.5, certainty=0.5, evidence_against_null=0.5,
        severity=0.5, world_contact=0.5, explanatory_virtue=0.5,
    )


def two_equal_candidates() -> Corpus:
    """Return a Corpus with two PENDING candidates c_held and c_conf.

    Both have:
    - identical StrengthVector => identical EIG/ValueVector
    - identical cost (via SIMPLE_COST)
    - an evaluation_plan with one DataHandle(ref="ds1") input
    - prior_cohorts set via provenance:
        c_held.prior_cohorts = ("other",)    -- disjoint from cohortX
        c_conf.prior_cohorts = ("cohortX",)  -- == cohort_of_ref["ds1"] in tests

    Equal value vectors mutually dominate each other, so both are off the Pareto front
    and fill-order density (via _severity_factor) is the only differentiator.
    """
    plan = _make_plan_with_data_handle("ds1")
    sv = _make_sv()

    prov_held = Provenance(
        generated_by=GenerationMode.IMPORTED,
        search_cardinality=1,
        prior_cohorts=("other",),
    )
    prov_conf = Provenance(
        generated_by=GenerationMode.IMPORTED,
        search_cardinality=1,
        prior_cohorts=("cohortX",),
    )

    c_held = Claim(
        id="c_held",
        title="held-out candidate",
        pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term="term-held"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        strength=sv,
        evaluation_plan=plan,
        provenance=prov_held,
    )
    c_conf = Claim(
        id="c_conf",
        title="confirmatory candidate",
        pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term="term-conf"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        strength=sv,
        evaluation_plan=plan,
        provenance=prov_conf,
    )

    return Corpus(
        claims=(c_held, c_conf),
        fdr_ledger=FDRLedger(target_fdr=0.05),
    )
