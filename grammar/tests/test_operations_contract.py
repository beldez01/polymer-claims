"""test_operations_contract.py — Task 10: optional EvaluationPlan.execution_contract.

Tests:
1. A plan WITH an execution_contract round-trips and model_dump includes the key.
2. A plan WITHOUT a contract has no "execution_contract" key in model_dump_json()
   (byte-identical commitment_hash to pre-Task-10).
3. ComputeGraph.content_hash is unaffected by the presence/absence of execution_contract.
4. A contract-bearing plan's model_dump_json() contains the contract
   (so commitment_hash binds it).
"""
import hashlib

from polymer_grammar.leaf import MeasurementBasis
from polymer_grammar.operations import (
    ComputeGraph,
    Comparator,
    EvaluationPlan,
    OperationNode,
    ProducedLeafSpec,
    SatisfactionCriterion,
)
from polymer_grammar.verification_policy import ExecutionContract

_SHA256_A = "sha256:" + "a" * 64
_SHA256_B = "sha256:" + "b" * 64

_CONTRACT = ExecutionContract(
    capability_id="cap-1",
    capability_version="v1.0",
    evidence_policy_ref=_SHA256_A,
    capability_descriptor_ref=_SHA256_B,
)


def _node() -> OperationNode:
    return OperationNode(
        id="n0",
        impl="builtin::test",
        produces=ProducedLeafSpec(
            leaf_kind="quantity",
            measurement_basis=MeasurementBasis.DERIVED,
        ),
    )


def _graph() -> ComputeGraph:
    return ComputeGraph(nodes=(_node(),), terminal="n0")


def _criterion() -> SatisfactionCriterion:
    return SatisfactionCriterion(comparator=Comparator.GT, threshold=0.5)


def _plan_no_contract() -> EvaluationPlan:
    return EvaluationPlan(graph=_graph(), criterion=_criterion())


def _plan_with_contract() -> EvaluationPlan:
    return EvaluationPlan(graph=_graph(), criterion=_criterion(), execution_contract=_CONTRACT)


# ---------------------------------------------------------------------------
# 1. Contract-bearing plan round-trips and model_dump includes the key
# ---------------------------------------------------------------------------

def test_contract_present_in_model_dump():
    plan = _plan_with_contract()
    dumped = plan.model_dump(mode="json")
    assert "execution_contract" in dumped
    ec = dumped["execution_contract"]
    assert ec["capability_id"] == "cap-1"
    assert ec["capability_version"] == "v1.0"


def test_contract_round_trips_via_json():
    plan = _plan_with_contract()
    json_str = plan.model_dump_json()
    plan2 = EvaluationPlan.model_validate_json(json_str)
    assert plan2.execution_contract is not None
    assert plan2.execution_contract.capability_id == "cap-1"


# ---------------------------------------------------------------------------
# 2. No-contract plan has NO "execution_contract" key (commitment_hash compat)
# ---------------------------------------------------------------------------

def test_no_contract_key_absent_from_model_dump_json():
    plan = _plan_no_contract()
    json_str = plan.model_dump_json()
    assert "execution_contract" not in json_str


def test_no_contract_key_absent_from_model_dump():
    plan = _plan_no_contract()
    dumped = plan.model_dump(mode="json")
    assert "execution_contract" not in dumped


def test_commitment_hash_byte_identical_for_no_contract_plan():
    """The sha256 of model_dump_json() must NOT change for a no-contract plan.

    We cannot reconstruct the exact pre-Task-10 hash (that ship has sailed), but we
    CAN assert that two independently-constructed no-contract plans hash identically
    AND that the JSON contains no 'execution_contract' substring — proving the
    serializer omits the field and old plans' commitment_hash is unbroken.
    """
    plan_a = _plan_no_contract()
    plan_b = _plan_no_contract()

    def _hash(p: EvaluationPlan) -> str:
        return "sha256:" + hashlib.sha256(p.model_dump_json().encode()).hexdigest()

    assert _hash(plan_a) == _hash(plan_b)
    assert "execution_contract" not in plan_a.model_dump_json()


# ---------------------------------------------------------------------------
# 3. ComputeGraph.content_hash unaffected by execution_contract
# ---------------------------------------------------------------------------

def test_graph_content_hash_unaffected_by_contract():
    """Plans sharing the same graph must have the same graph.content_hash,
    regardless of whether one carries an execution_contract."""
    plan_without = _plan_no_contract()
    plan_with = _plan_with_contract()

    assert plan_without.graph.content_hash == plan_with.graph.content_hash


# ---------------------------------------------------------------------------
# 4. Contract-bearing plan's model_dump_json() DOES contain the contract
# ---------------------------------------------------------------------------

def test_commitment_hash_includes_contract_when_present():
    plan = _plan_with_contract()
    json_str = plan.model_dump_json()
    assert "execution_contract" in json_str
    assert "cap-1" in json_str

    # The commitment hashes for contract vs no-contract plans must differ
    plan_no = _plan_no_contract()

    def _hash(p: EvaluationPlan) -> str:
        return hashlib.sha256(p.model_dump_json().encode()).hexdigest()

    assert _hash(plan) != _hash(plan_no)
