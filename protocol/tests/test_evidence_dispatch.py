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
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.0),
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


def test_commitment_hash_mismatch_skipped():
    """Gate-1 hash guard (execute.py:154): a claim whose CURRENT plan does not match its
    pending FDR test's commitment_hash is NOT dispatched — no record, no evidence execution.

    This is the pre-registration airtightness: a hypothesis mutated AFTER its α-slot was
    registered (so the plan now hashes to H' != the committed H) must not ride the slot
    reserved for the original hypothesis (post-hoc alteration / p-hacking). Companion to
    test_unregistered_evidence_claim_skipped (which pins the *missing-test* branch); together
    they close both no-dispatch branches of Gate-1 at the execute_ground level.
    """
    ctx = MaterializationContext(id="M1", api_version="v1", data_version="d1")

    descriptor = _make_descriptor()
    policy = _make_policy(descriptor.content_hash)
    cell = _make_cell(policy.content_hash)
    claim = _make_evidence_claim(cell, policy.content_hash)

    # Register the α-slot under a commitment hash that is NOT this claim's plan hash.
    real_ch = commitment_hash(claim)
    wrong_ch = f"sha256:{'d' * 64}"
    assert real_ch != wrong_ch  # sanity
    ledger = register_test(FDRLedger(target_fdr=0.05), claim.id, wrong_ch)
    corpus = Corpus(claims=(claim,), fdr_ledger=ledger)
    corpus = commit(corpus)

    # Runtime is otherwise fully valid — every downstream check WOULD pass; only Gate-1 stops it.
    trust_entry = ExecutorTrustEntry(
        descriptor_ref=descriptor.content_hash, owner="test-org", trusted=True, version="v1",
    )
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
    # Commitment mismatch → skipped BEFORE any pre-dispatch check → no record, no execution.
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


# ---------------------------------------------------------------------------
# Task 15: verify_stage evidence-route licensing tests
# ---------------------------------------------------------------------------


def _build_setup_with_e_value(e_value: float, provenance_e_value: float | None = None):
    """Like _build_full_setup but with configurable e_value (and optional tampered provenance_e_value).
    Returns (corpus, runtime) ready for run_cycle."""
    if provenance_e_value is None:
        provenance_e_value = e_value

    ctx = MaterializationContext(id="M1", api_version="v1", data_version="d1")
    descriptor = _make_descriptor()
    policy = _make_policy(descriptor.content_hash)
    cell = _make_cell(policy.content_hash)
    claim = _make_evidence_claim(cell, policy.content_hash)

    ledger = FDRLedger(target_fdr=0.05)
    ch = commitment_hash(claim)
    ledger = register_test(ledger, claim.id, ch)
    fdr_test = ledger.tests[0]

    corpus = Corpus(claims=(claim,), fdr_ledger=ledger)
    corpus = commit(corpus)

    prov = EvidenceProvenance(
        claim_id=claim.id,
        executor_descriptor_ref=descriptor.content_hash,
        evidence_policy_ref=policy.content_hash,
        benchmark_ref=_BENCH,
        baseline_config_ref=_SHA,
        baseline_predictions_ref=_SHA,
        predictor_config_ref=_SHA,
        capability_descriptor_ref=cell.content_hash,
        observed_advantage=0.1,
        theta0=0.0,
        e_value=provenance_e_value,
        execution_contract_digest=_SHA,
        fdr_test_index=fdr_test.index,
        alpha_allocated=fdr_test.alpha_allocated,
    )
    licensing_info = EvidenceLicensingInfo(
        route=LicenseRoute.EVIDENCE_LICENSED,
        verification_standing="single_source_baseline",
        evidence_provenance=prov,
        materialization=ctx,
    )
    record = ExecRecord(
        claim_id=claim.id,
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
    ee = EvidenceExecution(
        record=record,
        e_value=e_value,
        licensing_info=licensing_info,
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
        executor=_StubExecutor(descriptor.content_hash, ee),
    )
    return corpus, runtime, ctx


def test_evidence_licensed_via_run_cycle():
    """Discovery + grounded + provenance → claim LICENSED with EVIDENCE_LICENSED route.

    Uses e_value=100.0 (well above the e-LOND threshold for the first test slot).
    Checks: route, independence_tier=None, verification_standing, provenance.e_value==FDRTest.e_value.
    """
    from polymer_grammar import LicenseRoute as LR

    corpus, runtime, ctx = _build_setup_with_e_value(e_value=100.0)
    adapters = ()  # evidence claims skip the 2-adapter gate

    result = run_cycle(corpus, adapters, ctx, evidence_runtime=runtime)

    by_id = result.corpus.by_id()
    c = by_id["ev1"]
    assert c.status == Status.LICENSED, f"expected LICENSED, got {c.status}"
    assert c.licensing is not None
    assert c.licensing.route == LR.EVIDENCE_LICENSED
    assert c.licensing.independence_tier is None
    assert c.licensing.verification_standing == "single_source_baseline"
    assert c.licensing.evidence_provenance is not None
    # Provenance e_value must equal the resolved FDRTest e_value in the ledger
    ledger_test = next(
        t for t in result.corpus.fdr_ledger.tests if t.claim_id == "ev1"
    )
    assert c.licensing.evidence_provenance.e_value == ledger_test.e_value


def test_evidence_sub_threshold_stays_pending():
    """Sub-threshold e_value → no discovery → claim stays PENDING (not REFUTED, not REJECTED)."""
    corpus, runtime, ctx = _build_setup_with_e_value(e_value=0.5)
    adapters = ()

    result = run_cycle(corpus, adapters, ctx, evidence_runtime=runtime)

    c = result.corpus.by_id()["ev1"]
    assert c.status == Status.PENDING, f"expected PENDING, got {c.status}"
    assert c.pending_reason != PendingReason.EXECUTION_ERROR


def test_evidence_failure_pending_execution_error():
    """Executor credential mismatch → failure → claim PENDING with EXECUTION_ERROR."""
    corpus, cell, policy, descriptor, ctx, runtime = _build_full_setup()

    bad_cred = f"sha256:{'c' * 64}"
    bad_runtime = EvidenceRuntime(
        capability_registry=runtime.capability_registry,
        evidence_policy_registry=runtime.evidence_policy_registry,
        executor_descriptor_registry=runtime.executor_descriptor_registry,
        executor_trust_registry=runtime.executor_trust_registry,
        executor=_StubExecutor(bad_cred, None),  # type: ignore[arg-type]
    )

    adapters = ()
    result = run_cycle(corpus, adapters, ctx, evidence_runtime=bad_runtime)

    c = result.corpus.by_id()["ev1"]
    assert c.status == Status.PENDING
    assert c.pending_reason == PendingReason.EXECUTION_ERROR


def test_evidence_grounded_out_rejected():
    """Discovery but claim NOT in grounded extension → REJECTED DEFEAT_GROUNDED_OUT (fall-through)."""
    from polymer_grammar import RejectionReason

    from polymer_protocol.corpus import CycleScaffolding
    from polymer_protocol.verify import verify_stage

    ctx = MaterializationContext(id="M1", api_version="v1", data_version="d1")
    descriptor = _make_descriptor()
    policy = _make_policy(descriptor.content_hash)
    cell = _make_cell(policy.content_hash)
    claim = _make_evidence_claim(cell, policy.content_hash)

    ledger = FDRLedger(target_fdr=0.05)
    ch = commitment_hash(claim)
    ledger = register_test(ledger, claim.id, ch)
    fdr_test = ledger.tests[0]

    corpus = Corpus(claims=(claim,), fdr_ledger=ledger)
    corpus = commit(corpus)

    # Grounded extension is EMPTY — claim is NOT grounded (defeated/absent).
    scaffolding = CycleScaffolding(grounded_extension=(), frontier=())

    ev_record = ExecRecord(
        claim_id=claim.id,
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

    prov = EvidenceProvenance(
        claim_id=claim.id,
        executor_descriptor_ref=descriptor.content_hash,
        evidence_policy_ref=policy.content_hash,
        benchmark_ref=_BENCH,
        baseline_config_ref=_SHA,
        baseline_predictions_ref=_SHA,
        predictor_config_ref=_SHA,
        capability_descriptor_ref=cell.content_hash,
        observed_advantage=0.1,
        theta0=0.0,
        e_value=100.0,
        execution_contract_digest=_SHA,
        fdr_test_index=fdr_test.index,
        alpha_allocated=fdr_test.alpha_allocated,
    )
    info = EvidenceLicensingInfo(
        route=LicenseRoute.EVIDENCE_LICENSED,
        verification_standing="single_source_baseline",
        evidence_provenance=prov,
        materialization=ctx,
    )

    out = verify_stage(
        corpus, scaffolding, (ev_record,),
        evidence={"ev1": 100.0},
        evidence_licensing={"ev1": info},
    )

    c = out.by_id()["ev1"]
    assert c.status == Status.REJECTED
    assert c.rejection_reason == RejectionReason.DEFEAT_GROUNDED_OUT


def test_evidence_ledger_equality_raises_on_e_value_mismatch():
    """Tampered provenance.e_value (99.0) vs ledger e_value (100.0) → ValueError."""
    corpus, runtime, ctx = _build_setup_with_e_value(
        e_value=100.0,          # what goes into ev_map → resolves FDR test to 100.0
        provenance_e_value=99.0,  # tampered: will NOT match ledger's 100.0
    )
    adapters = ()

    with pytest.raises(ValueError, match="evidence provenance/ledger mismatch"):
        run_cycle(corpus, adapters, ctx, evidence_runtime=runtime)


def test_altered_precedence_over_evidence_failure():
    """A claim in altered_ids AND evidence_failures → REJECTED HYPOTHESIS_ALTERED (not EXECUTION_ERROR).

    Directly calls verify_stage with a FDR test registered under a wrong commitment_hash
    (simulating post-hoc alteration) and the same claim_id in evidence_failures.
    """
    from polymer_grammar import RejectionReason

    from polymer_protocol.corpus import CycleScaffolding
    from polymer_protocol.verify import verify_stage

    descriptor = _make_descriptor()
    policy = _make_policy(descriptor.content_hash)
    cell = _make_cell(policy.content_hash)
    claim = _make_evidence_claim(cell, policy.content_hash)

    real_ch = commitment_hash(claim)
    wrong_ch = f"sha256:{'d' * 64}"
    assert real_ch != wrong_ch  # sanity

    ledger = FDRLedger(target_fdr=0.05)
    ledger = register_test(ledger, claim.id, wrong_ch)  # register with WRONG hash

    corpus = Corpus(claims=(claim,), fdr_ledger=ledger)
    corpus = commit(corpus)  # sets provenance.preregistration_hash = real lock

    scaffolding = CycleScaffolding(grounded_extension=(claim.id,), frontier=())

    ev_record = ExecRecord(
        claim_id=claim.id,
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

    # Pass claim in evidence_failures to test precedence (altered should win).
    evidence_failures = {claim.id: object()}

    out = verify_stage(
        corpus, scaffolding, (ev_record,),
        evidence={"ev1": 3.0},          # triggers the alteration check
        evidence_failures=evidence_failures,
    )

    c = out.by_id()[claim.id]
    assert c.status == Status.REJECTED
    assert c.rejection_reason == RejectionReason.HYPOTHESIS_ALTERED


# ---------------------------------------------------------------------------
# Spec §4 chain link: criterion.threshold == policy.theta0
# ---------------------------------------------------------------------------


def test_criterion_threshold_mismatch_predispatch_failure():
    """Claim with criterion.threshold != policy.theta0 → pre_dispatch policy_mismatch.

    The claim is registered CONSISTENTLY — commitment_hash in the FDR ledger is
    computed from THIS claim (threshold=0.5), so gate-1 passes and the claim is
    NOT on the HYPOTHESIS_ALTERED path.  The new check 8 (criterion.threshold ==
    policy.theta0) catches the divergence and produces a pre_dispatch failure.

    Asserts via run_cycle: Status.PENDING + PendingReason.EXECUTION_ERROR, not licensed.
    """
    from polymer_protocol.cycle import run_cycle

    ctx = MaterializationContext(id="M-div", api_version="v1", data_version="d1")

    descriptor = _make_descriptor()
    policy = _make_policy(descriptor.content_hash)  # theta0=0.0
    cell = _make_cell(policy.content_hash)

    # Build a claim whose criterion.threshold (0.5) diverges from policy.theta0 (0.0).
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
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.5),
        execution_contract=ExecutionContract(
            capability_id=cell.capability_id,
            capability_version=cell.capability_version,
            evidence_policy_ref=policy.content_hash,
            capability_descriptor_ref=cell.content_hash,
        ),
    )
    divergent_claim = Claim(
        id="ev-div",
        title="Divergent evidence claim",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="term-ev-div"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        evaluation_plan=plan,
    )

    # Register using THIS claim's commitment_hash → gate-1 passes (not the altered path).
    ledger = FDRLedger(target_fdr=0.05)
    ch = commitment_hash(divergent_claim)
    ledger = register_test(ledger, divergent_claim.id, ch)

    corpus = Corpus(claims=(divergent_claim,), fdr_ledger=ledger)
    corpus = commit(corpus)

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
        executor=_StubExecutor(descriptor.content_hash, None),  # type: ignore[arg-type]
    )

    # Directly verify the pre-dispatch failure (commitment matches → new check fires).
    _out, records, evidence_executions = execute_ground(
        corpus, (), ctx, evidence_runtime=runtime,
    )
    assert len(evidence_executions) == 1, "expected exactly one EvidenceExecution"
    ee = evidence_executions[0]
    assert ee.failure_reason is not None, "expected a pre_dispatch failure"
    assert ee.failure_reason.stage == "pre_dispatch"
    assert ee.failure_reason.reason == "policy_mismatch"
    assert ee.e_value is None
    assert ee.licensing_info is None

    # Full cycle: claim must end PENDING with EXECUTION_ERROR, not licensed.
    result = run_cycle(corpus, (), ctx, evidence_runtime=runtime)
    c = result.corpus.by_id()["ev-div"]
    assert c.status == Status.PENDING, f"expected PENDING, got {c.status}"
    assert c.pending_reason == PendingReason.EXECUTION_ERROR
    assert c.licensing is None
