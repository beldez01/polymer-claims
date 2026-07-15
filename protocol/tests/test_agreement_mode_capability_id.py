"""Audit finding 4 — agreement mode resolves by (capability_id, version), not operation_impl.

Two cells sharing operation_impl (as expression::floor and expression::floor_feature do) must each
resolve to THEIR OWN agreement mode via the claim's execution_contract, not the first impl match.
"""
from __future__ import annotations

from polymer_grammar import (
    CapabilityCell,
    CapabilityRegistry,
    CategoricalLeaf,
    Comparator,
    ComputeGraph,
    DataHandle,
    DataRefKind,
    EvaluationPlan,
    ExecutionContract,
    OperationNode,
    OracleRequirement,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    SatisfactionCriterion,
    Status,
    SubjectRequirement,
)

from polymer_protocol.corpus import Claim
from polymer_protocol.execute import _agreement_mode_for

_PAT = PatternRef(id="adjusted_effect", version="v1")


def _cell(cap_id: str, mode: str) -> CapabilityCell:
    return CapabilityCell(
        capability_id=cap_id, capability_version="v1", operation_impl="shared::impl",
        title=cap_id, pattern=_PAT, subject=SubjectRequirement(mode="forbidden"), param_schema=(),
        produced=ProducedLeafSpec(leaf_kind="quantity"), allowed_comparators=(Comparator.GE,),
        eligible_adapter_identities=("a", "b"),
        oracle=OracleRequirement(), data_ref_kind=DataRefKind.SE_CONTRACT,
        claim_leaf_kinds=("quantity",), criterion_target="threshold", agreement_mode=mode,
    )


def _claim(cap_id: str) -> Claim:
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(OperationNode(
            id="n0", impl="shared::impl", inputs=(DataHandle(ref="se:x@1"),),
            produces=ProducedLeafSpec(leaf_kind="quantity")),), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.GE, threshold=0.0),
        execution_contract=ExecutionContract(
            capability_id=cap_id, capability_version="v1",
            evidence_policy_ref="sha256:" + "a" * 64, capability_descriptor_ref="sha256:" + "b" * 64),
    )
    return Claim(id="c", title="c", pattern=_PAT, leaves=(CategoricalLeaf(ontology_term="t"),),
                 status=Status.PENDING, pending_reason=PendingReason.UNTESTED, evaluation_plan=plan)


def test_agreement_mode_resolves_by_capability_id_not_first_impl_match():
    # cap::a is registered FIRST and shares operation_impl with cap::b but has a different mode.
    reg = CapabilityRegistry(cells=(_cell("cap::a", "tight_numeric"),
                                    _cell("cap::b", "both_satisfy_criterion")))
    # Without the fix, both claims would get cap::a's mode (first impl match). With it, each gets its own.
    assert _agreement_mode_for(_claim("cap::b"), reg) == "both_satisfy_criterion"
    assert _agreement_mode_for(_claim("cap::a"), reg) == "tight_numeric"
