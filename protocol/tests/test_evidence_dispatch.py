"""test_evidence_dispatch.py — TDD tests for evidence claim dispatch (Tasks 13+14).

Uses grammar + protocol DTOs only. No polymer_claims imports.
"""
from __future__ import annotations

import hashlib
import json

import pytest
from polymer_grammar import (
    CategoricalLeaf,
    CapabilityCell,
    CapabilityRegistry,
    Claim,
    Comparator,
    Component,
    ComputeGraph,
    DataHandle,
    DataRefKind,
    EvaluationPlan,
    EvaluationResult,
    EvidenceLicensingInfo,
    EvidencePolicy,
    EvidencePolicyRegistry,
    EvidenceProvenance,
    ExecutionContract,
    ExecutorDescriptor,
    ExecutorDescriptorRegistry,
    ExecutorTrustEntry,
    ExecutorTrustRegistry,
    ExecValue,
    FDRLedger,
    IdentityAdapter,
    LicenseRoute,
    MaterializationContext,
    OperationNode,
    OracleRequirement,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    ReferenceAdapter,
    SamplingRegime,
    SatisfactionCriterion,
    SatisfactionVerdict,
    Status,
    SubjectRequirement,
    VerificationPolicy,
    VerifiedEvaluation,
    commitment_hash,
    register_test,
)

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus, ExecRecord
from polymer_protocol.cycle import run_cycle
from polymer_protocol.evidence_executor import EvidenceExecution, EvidenceRuntime
from polymer_protocol.execute import execute_ground

_HEX64 = "a" * 64
_SHA = f"sha256:{_HEX64}"
_BENCH = f"bench:sha256:{_HEX64}"
_BENCH2 = f"bench:sha256:{'b' * 64}"


def _sha(obj):
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


# ---------------------------------------------------------------------------
# Stub executor
# ---------------------------------------------------------------------------


class _StubExecutor:
    def __init__(self, cred: str, result: EvidenceExecution):
        self._cred = cred
        self._result = result

    def credential(self) -> str:
        return self._cred

    def execute(self, claim, cell, policy, ctx, fdr_test) -> EvidenceExecution:
        return self._result


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def _make_descriptor() -> ExecutorDescriptor:
    return ExecutorDescriptor(
        version="v1",
        components=(
            Component(role="predictor", identity="p1", implementation_hash=_SHA, config_hash=_SHA),
            Component(role="baseline_predictor", identity="bp1", implementation_hash=_SHA, config_hash=_SHA),
            Component(role="scorer", identity="s1", implementation_hash=_SHA, config_hash=_SHA),
            Component(role="evidence_transform", identity="et1", implementation_hash=_SHA, config_hash=_SHA),
        ),
    )


def _make_policy(descriptor_content_hash: str) -> EvidencePolicy:
    return EvidencePolicy(
        policy_id="ev-policy",
        version="v1",
        null_family="paired_bounded_mean_betting",
        theta0=0.0,
        statistic="advantage",
        support="[-1,1]",
        sampling_regime=SamplingRegime.IID_EXAMPLES,
        baseline_config_ref=_SHA,
        calibration_population_ref=_SHA,
        predictor_config_ref=_SHA,
        executor_descriptor_ref=descriptor_content_hash,
        evalue_transform="paired_wsr_betting",
    )


def _make_cell(policy_content_hash: str) -> CapabilityCell:
    vp = VerificationPolicy(
        execution="single",
        result_rule="evalue_discovery",
        independence_requirement="baseline_ground_truth",
        evidence_policy_ref=policy_content_hash,
        min_adapters=1,
    )
    return CapabilityCell(
        capability_id="ev-cap",
        capability_version="v1",
        operation_impl="ev::bench_eval",
        title="Evidence benchmark evaluation",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        subject=SubjectRequirement(mode="forbidden"),
        param_schema=(),
        produced=ProducedLeafSpec(leaf_kind="categorical"),
        allowed_comparators=(Comparator.LT,),
        eligible_adapter_identities=("ev-adapter",),
        min_executing_adapters=1,
        oracle=OracleRequirement(),
        data_ref_kind=DataRefKind.BENCHMARK,
        claim_leaf_kinds=("categorical",),
        criterion_target="threshold",
        verification_policy=vp,
    )


def _make_evidence_claim(cell: CapabilityCell, policy_content_hash: str) -> Claim:
    plan = EvaluationPlan(
        graph=ComputeGraph(
            nodes=(OperationNode(
                id="n0",
                impl=cell.operation_impl,
                inputs=(DataHandle(ref=_BENCH),),
                produces=cell.produced,
            ),),
            terminal="n0",
        ),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
        execution_contract=ExecutionContract(
            capability_id=cell.capability_id,
            capability_version=cell.capability_version,
            evidence_policy_ref=policy_content_hash,
            capability_descriptor_ref=cell.content_hash,
        ),
    )
    return Claim(
        id="ev1",
        title="Evidence claim",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="term-ev1"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        evaluation_plan=plan,
    )


def _make_success_ee(
    claim_id: str,
    descriptor_content_hash: str,
    policy_content_hash: str,
    cell_content_hash: str,
    ctx: MaterializationContext,
    fdr_test_index: int,
    alpha_allocated: float,
) -> EvidenceExecution:
    prov = EvidenceProvenance(
        claim_id=claim_id,
        executor_descriptor_ref=descriptor_content_hash,
        evidence_policy_ref=policy_content_hash,
        benchmark_ref=_BENCH,
        baseline_config_ref=_SHA,
        baseline_predictions_ref=_SHA,
        predictor_config_ref=_SHA,
        capability_descriptor_ref=cell_content_hash,
        observed_advantage=0.1,
        theta0=0.0,
        e_value=3.0,
        execution_contract_digest=_SHA,
        fdr_test_index=fdr_test_index,
        alpha_allocated=alpha_allocated,
    )
    licensing_info = EvidenceLicensingInfo(
        route=LicenseRoute.EVIDENCE_LICENSED,
        verification_standing="single_source_baseline",
        evidence_provenance=prov,
        materialization=ctx,
    )
    record = ExecRecord(
        claim_id=claim_id,
        evaluation=VerifiedEvaluation(
            results=(EvaluationResult(
                verdict=SatisfactionVerdict.UNDETERMINED,
                terminal=ExecValue(value=None),
                nodes=(),
                adapter_identity="ev-adapter",
                status="complete",
            ),),
            agreement=False,
            satisfaction=None,
        ),
    )
    return EvidenceExecution(
        record=record,
        e_value=3.0,
        licensing_info=licensing_info,
    )


def _build_full_setup(claim_id: str = "ev1"):
    """Return (corpus, cell, policy, descriptor, ctx, runtime) for a committed evidence claim."""
    ctx = MaterializationContext(id="M1", api_version="v1", data_version="d1")

    descriptor = _make_descriptor()
    policy = _make_policy(descriptor.content_hash)
    cell = _make_cell(policy.content_hash)
    claim = _make_evidence_claim(cell, policy.content_hash)
    claim = Claim(**{**claim.model_dump(), "id": claim_id, "title": f"Evidence claim {claim_id}"})
    # Rebuild plan with correct claim_id (claim id doesn't affect plan content)

    ledger = FDRLedger(target_fdr=0.05)
    ch = commitment_hash(claim)
    ledger = register_test(ledger, claim.id, ch)
    fdr_test = ledger.tests[0]

    corpus = Corpus(claims=(claim,), fdr_ledger=ledger)
    corpus = commit(corpus)

    success_ee = _make_success_ee(
        claim_id=claim.id,
        descriptor_content_hash=descriptor.content_hash,
        policy_content_hash=policy.content_hash,
        cell_content_hash=cell.content_hash,
        ctx=ctx,
        fdr_test_index=fdr_test.index,
        alpha_allocated=fdr_test.alpha_allocated,
    )

    trust_entry = ExecutorTrustEntry(
        descriptor_ref=descriptor.content_hash,
        owner="test-org",
        trusted=True,
        version="v1",
    )
    runtime = EvidenceRuntime(
        capability_registry=CapabilityRegistry(cells=(cell,)),
        evidence_policy_registry=EvidencePolicyRegistry(policies=(policy,)),
        executor_descriptor_registry=ExecutorDescriptorRegistry(descriptors=(descriptor,)),
        executor_trust_registry=ExecutorTrustRegistry(entries=(trust_entry,)),
        executor=_StubExecutor(descriptor.content_hash, success_ee),
    )
    return corpus, cell, policy, descriptor, ctx, runtime


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_none_runtime_is_byte_identical():
    """run_cycle with evidence_runtime=None vs omitted: byte-identical corpus result."""
    from tests.conftest import make_claim, make_plan

    ctx = MaterializationContext(id="M1", api_version="v1", data_version="d1")
    adapters = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05))

    r1 = run_cycle(corpus, adapters, ctx)
    r2 = run_cycle(corpus, adapters, ctx, evidence_runtime=None)

    assert r1.corpus.model_dump_json() == r2.corpus.model_dump_json()


def test_evidence_claim_dispatched_to_executor():
    """Evidence claim with all checks passing: dispatched to executor, EvidenceExecution produced.

    SelfLicensingError must NOT be raised (evidence claims skip the 2-adapter verify)."""
    corpus, cell, policy, descriptor, ctx, runtime = _build_full_setup()

    # Single adapter or empty — evidence claims don't call verify()
    _out, records, evidence_executions = execute_ground(
        corpus, (), ctx, evidence_runtime=runtime,
    )
    assert len(evidence_executions) == 1
    ee = evidence_executions[0]
    assert ee.failure_reason is None
    assert ee.e_value == 3.0
    # The record should be in records too
    assert len(records) == 1
    assert records[0].claim_id == "ev1"


def test_unregistered_evidence_claim_skipped():
    """Evidence claim with no pending FDR test in ledger: NO ExecRecord produced."""
    ctx = MaterializationContext(id="M1", api_version="v1", data_version="d1")

    descriptor = _make_descriptor()
    policy = _make_policy(descriptor.content_hash)
    cell = _make_cell(policy.content_hash)
    claim = _make_evidence_claim(cell, policy.content_hash)

    # Empty ledger — no FDR test registered
    ledger = FDRLedger(target_fdr=0.05)
    corpus = Corpus(claims=(claim,), fdr_ledger=ledger)
    corpus = commit(corpus)

    # Build a valid runtime (all checks would pass if we got past the FDR gate)
    trust_entry = ExecutorTrustEntry(
        descriptor_ref=descriptor.content_hash,
        owner="test-org",
        trusted=True,
        version="v1",
    )
    # Need a placeholder EvidenceExecution for the stub (won't be called)
    runtime = EvidenceRuntime(
        capability_registry=CapabilityRegistry(cells=(cell,)),
        evidence_policy_registry=EvidencePolicyRegistry(policies=(policy,)),
        executor_descriptor_registry=ExecutorDescriptorRegistry(descriptors=(descriptor,)),
        executor_trust_registry=ExecutorTrustRegistry(entries=(trust_entry,)),
        executor=_StubExecutor(descriptor.content_hash, None),  # type: ignore[arg-type]
    )

    _out, records, evidence_executions = execute_ground(
        corpus, (), ctx, evidence_runtime=runtime,
    )
    # No FDR test → skipped entirely, no record produced
    assert records == ()
    assert evidence_executions == ()


def test_credential_mismatch_produces_predispatch_failure():
    """Executor with wrong credential → EvidenceExecution with pre_dispatch credential_mismatch."""
    corpus, cell, policy, descriptor, ctx, runtime = _build_full_setup()

    # Build a runtime with a wrong credential
    bad_cred = f"sha256:{'c' * 64}"
    bad_runtime = EvidenceRuntime(
        capability_registry=runtime.capability_registry,
        evidence_policy_registry=runtime.evidence_policy_registry,
        executor_descriptor_registry=runtime.executor_descriptor_registry,
        executor_trust_registry=runtime.executor_trust_registry,
        executor=_StubExecutor(bad_cred, None),  # type: ignore[arg-type]
    )

    _out, records, evidence_executions = execute_ground(
        corpus, (), ctx, evidence_runtime=bad_runtime,
    )
    assert len(evidence_executions) == 1
    ee = evidence_executions[0]
    assert ee.failure_reason is not None
    assert ee.failure_reason.reason == "credential_mismatch"
    assert ee.failure_reason.stage == "pre_dispatch"


def test_collision_raises_on_dual_evidence():
    """run_cycle with executor returning SUCCESS for 'ev1' + caller supplies evidence={'ev1': 2.0}
    → raises ValueError (collision)."""
    corpus, cell, policy, descriptor, ctx, runtime = _build_full_setup()
    adapters = (IdentityAdapter(), ReferenceAdapter(identity="reference"))

    with pytest.raises(ValueError, match="evidence collision"):
        run_cycle(
            corpus, adapters, ctx,
            evidence_runtime=runtime,
            evidence={"ev1": 2.0},
        )
