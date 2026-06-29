"""Tests for BenchmarkEvidenceExecutor (Sub-task B, Task 12).

TDD: failing tests first — implementation lives in benchmark_capability.py.
"""
from __future__ import annotations

import math
from types import SimpleNamespace


from polymer_grammar import (
    CategoricalLeaf,
    FDRTest,
    MaterializationContext,
    PatternRef,
    SamplingRegime,
    Status,
)
from polymer_grammar.evidence_policy import EvidencePolicy
from polymer_grammar.licensing import LicenseRoute, SatisfactionVerdict
from polymer_grammar.operations import (
    Comparator,
    ComputeGraph,
    DataHandle,
    EvaluationPlan,
    OperationNode,
    ProducedLeafSpec,
    SatisfactionCriterion,
)

from polymer_claims._hashing import canonical_sha256
from polymer_claims.benchmark_adapter import (
    BenchmarkArtifact,
    BenchmarkExample,
    FixtureBaselineAdapter,
    FixtureModelAdapter,
)
from polymer_claims.benchmark_evidence import paired_advantage_evalue, score_advantage
from polymer_grammar.claim import Claim

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DGPDIGEST = "sha256:" + "a" * 64
_REGIME = SamplingRegime.IID_EXAMPLES
_HEX64 = "b" * 64
_FALLBACK_SHA = f"sha256:{_HEX64}"


def _make_artifact_strong(n: int = 60) -> BenchmarkArtifact:
    """Return an artifact where labels = model predictions (model always correct)."""
    model_adapter = FixtureModelAdapter()
    # Build placeholder examples first to get model predictions
    placeholder = tuple(
        BenchmarkExample(
            example_id=f"e{i:04d}",
            features=(("idx", str(i)),),
            label="neg",  # placeholder
        )
        for i in range(n)
    )
    model_pv = model_adapter.predict(placeholder)
    # Set labels so model is always correct
    examples = tuple(
        BenchmarkExample(
            example_id=ex.example_id,
            features=ex.features,
            label=pred,
        )
        for ex, (_, pred) in zip(placeholder, model_pv.predictions)
    )
    return BenchmarkArtifact(
        examples=examples,
        target_population="test-population",
        sampling_regime=_REGIME,
        version="v1",
        sampling_seed=42,
        dgp_digest=_DGPDIGEST,
    )


def _config_hash(config: dict) -> str:
    return canonical_sha256(config)


def _make_policy(
    artifact: BenchmarkArtifact,
    predictor: FixtureModelAdapter,
    baseline: FixtureBaselineAdapter,
    executor_descriptor_ref: str = _FALLBACK_SHA,
) -> EvidencePolicy:
    return EvidencePolicy(
        policy_id="test-policy-v1",
        version="1",
        null_family="paired_bounded_mean_betting",
        theta0=0.0,
        statistic="paired_advantage",
        support="[-1,1]",
        sampling_regime=_REGIME,
        baseline_config_ref=_config_hash(baseline.config),
        calibration_population_ref=artifact.content_hash,
        predictor_config_ref=_config_hash(predictor.config),
        executor_descriptor_ref=executor_descriptor_ref,
        evalue_transform="paired_wsr_betting",
    )


def _make_claim(artifact: BenchmarkArtifact) -> Claim:
    """Minimal valid claim whose terminal DataHandle points at the artifact."""
    node = OperationNode(
        id="n0",
        impl="benchmark::score_advantage",
        inputs=(DataHandle(ref=artifact.ref),),
        params=(),
        produces=ProducedLeafSpec(leaf_kind="quantity"),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.GT, threshold=0.0),
    )
    return Claim(
        id="claim-benchmark-001",
        title="Benchmark advantage claim",
        pattern=PatternRef(id="model_delta_over_baseline", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="test-outcome"),),
        status=Status.CONJECTURED,
        evaluation_plan=plan,
    )


def _stub_cell(sha: str = _FALLBACK_SHA) -> SimpleNamespace:
    return SimpleNamespace(content_hash=sha)


def _make_fdr_test(claim_id: str = "claim-benchmark-001") -> FDRTest:
    return FDRTest(
        index=1,
        claim_id=claim_id,
        e_value=None,
        alpha_allocated=0.05,
        discovery=False,
    )


def _make_ctx() -> MaterializationContext:
    return MaterializationContext(id="test-mat", api_version="1.0", data_version="test@v1")


# ---------------------------------------------------------------------------
# Shared fixture setup
# ---------------------------------------------------------------------------


def _build_executor(artifact: BenchmarkArtifact | None = None):
    """Build a BenchmarkEvidenceExecutor with strong artifact."""
    from polymer_claims.benchmark_capability import BenchmarkEvidenceExecutor

    if artifact is None:
        artifact = _make_artifact_strong()

    predictor = FixtureModelAdapter()
    baseline = FixtureBaselineAdapter()

    store = {artifact.content_hash: artifact}

    # Build the executor — policy is determined by the adapters' configs
    executor = BenchmarkEvidenceExecutor(
        predictor=predictor,
        baseline_predictor=baseline,
        scorer=score_advantage,
        transform=paired_advantage_evalue,
        artifact_store=store,
    )
    return executor, predictor, baseline, artifact


# ---------------------------------------------------------------------------
# credential() — format and stability
# ---------------------------------------------------------------------------


def test_credential_format():

    executor, _, _, _ = _build_executor()
    cred = executor.credential()
    import re
    assert re.match(r"^sha256:[0-9a-f]{64}$", cred), f"bad format: {cred!r}"


def test_credential_is_stable():
    executor, _, _, _ = _build_executor()
    assert executor.credential() == executor.credential()


def test_credential_changes_when_baseline_swapped():
    """Swapping the baseline to a different adapter changes the credential."""
    from polymer_claims.benchmark_capability import BenchmarkEvidenceExecutor

    artifact = _make_artifact_strong()
    store = {artifact.content_hash: artifact}

    predictor = FixtureModelAdapter()
    baseline_a = FixtureBaselineAdapter(identity="baseline-a", config={"version": "1"})
    baseline_b = FixtureBaselineAdapter(identity="baseline-b", config={"version": "2"})

    ex_a = BenchmarkEvidenceExecutor(
        predictor=predictor,
        baseline_predictor=baseline_a,
        scorer=score_advantage,
        transform=paired_advantage_evalue,
        artifact_store=store,
    )
    ex_b = BenchmarkEvidenceExecutor(
        predictor=predictor,
        baseline_predictor=baseline_b,
        scorer=score_advantage,
        transform=paired_advantage_evalue,
        artifact_store=store,
    )
    assert ex_a.credential() != ex_b.credential()


# ---------------------------------------------------------------------------
# Happy path — execute() returns success EvidenceExecution
# ---------------------------------------------------------------------------


def test_execute_returns_evidence_execution():
    from polymer_protocol.evidence_executor import EvidenceExecution

    executor, predictor, baseline, artifact = _build_executor()
    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    claim = _make_claim(artifact)
    cell = _stub_cell()
    ctx = _make_ctx()
    fdr_test = _make_fdr_test(claim.id)

    result = executor.execute(claim, cell, policy, ctx, fdr_test)
    assert isinstance(result, EvidenceExecution)


def test_execute_success_e_value_positive():
    executor, predictor, baseline, artifact = _build_executor()
    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    claim = _make_claim(artifact)
    cell = _stub_cell()
    ctx = _make_ctx()
    fdr_test = _make_fdr_test(claim.id)

    result = executor.execute(claim, cell, policy, ctx, fdr_test)
    assert result.failure_reason is None
    assert result.e_value is not None
    assert result.e_value > 1.0, f"expected e_value > 1, got {result.e_value}"


def test_execute_success_e_value_finite():
    executor, predictor, baseline, artifact = _build_executor()
    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    claim = _make_claim(artifact)
    cell = _stub_cell()
    ctx = _make_ctx()
    fdr_test = _make_fdr_test(claim.id)

    result = executor.execute(claim, cell, policy, ctx, fdr_test)
    assert result.e_value is not None
    assert math.isfinite(result.e_value)


def test_execute_success_route_is_evidence_licensed():
    executor, predictor, baseline, artifact = _build_executor()
    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    claim = _make_claim(artifact)
    cell = _stub_cell()
    ctx = _make_ctx()
    fdr_test = _make_fdr_test(claim.id)

    result = executor.execute(claim, cell, policy, ctx, fdr_test)
    assert result.licensing_info is not None
    assert result.licensing_info.route == LicenseRoute.EVIDENCE_LICENSED


def test_execute_success_provenance_populated():
    executor, predictor, baseline, artifact = _build_executor()
    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    claim = _make_claim(artifact)
    cell = _stub_cell()
    ctx = _make_ctx()
    fdr_test = _make_fdr_test(claim.id)

    result = executor.execute(claim, cell, policy, ctx, fdr_test)
    assert result.licensing_info is not None
    prov = result.licensing_info.evidence_provenance
    assert prov.claim_id == claim.id
    assert prov.benchmark_ref == artifact.ref
    assert prov.theta0 == policy.theta0
    assert prov.e_value == result.e_value
    assert prov.fdr_test_index == fdr_test.index
    assert prov.alpha_allocated == fdr_test.alpha_allocated


def test_execute_success_record_verdict_undetermined():
    executor, predictor, baseline, artifact = _build_executor()
    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    claim = _make_claim(artifact)
    cell = _stub_cell()
    ctx = _make_ctx()
    fdr_test = _make_fdr_test(claim.id)

    result = executor.execute(claim, cell, policy, ctx, fdr_test)
    assert len(result.record.evaluation.results) == 1
    assert result.record.evaluation.results[0].verdict == SatisfactionVerdict.UNDETERMINED


def test_execute_success_record_satisfaction_none():
    executor, predictor, baseline, artifact = _build_executor()
    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    claim = _make_claim(artifact)
    cell = _stub_cell()
    ctx = _make_ctx()
    fdr_test = _make_fdr_test(claim.id)

    result = executor.execute(claim, cell, policy, ctx, fdr_test)
    assert result.record.evaluation.satisfaction is None


def test_execute_success_record_terminal_value_is_observed_advantage():
    executor, predictor, baseline, artifact = _build_executor()
    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    claim = _make_claim(artifact)
    cell = _stub_cell()
    ctx = _make_ctx()
    fdr_test = _make_fdr_test(claim.id)

    result = executor.execute(claim, cell, policy, ctx, fdr_test)
    terminal_value = result.record.evaluation.results[0].terminal.value
    assert terminal_value is not None
    # Observed advantage is in [-1, 1]
    assert -1.0 <= terminal_value <= 1.0


def test_execute_state_validator_passes():
    """The returned EvidenceExecution must pass its own Pydantic state validator."""
    from polymer_protocol.evidence_executor import EvidenceExecution

    executor, predictor, baseline, artifact = _build_executor()
    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    claim = _make_claim(artifact)
    cell = _stub_cell()
    ctx = _make_ctx()
    fdr_test = _make_fdr_test(claim.id)

    # If the state validator fails, construction of EvidenceExecution raises ValidationError
    result = executor.execute(claim, cell, policy, ctx, fdr_test)
    # Re-instantiate to confirm round-trip validatability
    ee = EvidenceExecution(
        record=result.record,
        e_value=result.e_value,
        licensing_info=result.licensing_info,
        failure_reason=result.failure_reason,
    )
    assert ee.failure_reason is None


# ---------------------------------------------------------------------------
# FAILURE path — tampered benchmark ref → digest_mismatch
# ---------------------------------------------------------------------------


def test_tampered_benchmark_ref_returns_failure():
    executor, predictor, baseline, artifact = _build_executor()
    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    # Tamper: claim DataHandle points to wrong ref
    node = OperationNode(
        id="n0",
        impl="benchmark::score_advantage",
        inputs=(DataHandle(ref="bench:" + "c" * 64),),  # wrong ref
        params=(),
        produces=ProducedLeafSpec(leaf_kind="quantity"),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.GT, threshold=0.0),
    )
    tampered_claim = Claim(
        id="claim-benchmark-001",
        title="Tampered claim",
        pattern=PatternRef(id="model_delta_over_baseline", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="test-outcome"),),
        status=Status.CONJECTURED,
        evaluation_plan=plan,
    )

    cell = _stub_cell()
    ctx = _make_ctx()
    fdr_test = _make_fdr_test(tampered_claim.id)

    result = executor.execute(tampered_claim, cell, policy, ctx, fdr_test)
    assert result.failure_reason is not None
    assert result.failure_reason.reason == "digest_mismatch"
    assert result.e_value is None


def test_tampered_benchmark_ref_failure_record_error_status():
    executor, predictor, baseline, artifact = _build_executor()
    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    node = OperationNode(
        id="n0",
        impl="benchmark::score_advantage",
        inputs=(DataHandle(ref="bench:" + "d" * 64),),
        params=(),
        produces=ProducedLeafSpec(leaf_kind="quantity"),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.GT, threshold=0.0),
    )
    tampered_claim = Claim(
        id="claim-benchmark-001",
        title="Tampered",
        pattern=PatternRef(id="model_delta_over_baseline", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="test-outcome"),),
        status=Status.CONJECTURED,
        evaluation_plan=plan,
    )

    result = executor.execute(
        tampered_claim, _stub_cell(), policy, _make_ctx(), _make_fdr_test(tampered_claim.id)
    )
    assert result.record.evaluation.results[0].status == "error"
    assert result.record.evaluation.results[0].terminal.value is None


# ---------------------------------------------------------------------------
# FAILURE path — artifact not in store → digest_mismatch
# ---------------------------------------------------------------------------


def test_artifact_absent_from_store_returns_failure():
    from polymer_claims.benchmark_capability import BenchmarkEvidenceExecutor

    artifact = _make_artifact_strong()
    predictor = FixtureModelAdapter()
    baseline = FixtureBaselineAdapter()

    # Store is empty — artifact not registered
    executor = BenchmarkEvidenceExecutor(
        predictor=predictor,
        baseline_predictor=baseline,
        scorer=score_advantage,
        transform=paired_advantage_evalue,
        artifact_store={},
    )

    policy = _make_policy(
        artifact, predictor, baseline,
        executor_descriptor_ref=executor.credential(),
    )
    claim = _make_claim(artifact)
    result = executor.execute(claim, _stub_cell(), policy, _make_ctx(), _make_fdr_test(claim.id))
    assert result.failure_reason is not None
    assert result.failure_reason.reason == "digest_mismatch"


# ---------------------------------------------------------------------------
# FAILURE path — policy_mismatch on baseline_config_ref
# ---------------------------------------------------------------------------


def test_baseline_config_mismatch_returns_failure():
    from polymer_claims.benchmark_capability import BenchmarkEvidenceExecutor

    artifact = _make_artifact_strong()
    predictor = FixtureModelAdapter()
    baseline = FixtureBaselineAdapter()

    executor = BenchmarkEvidenceExecutor(
        predictor=predictor,
        baseline_predictor=baseline,
        scorer=score_advantage,
        transform=paired_advantage_evalue,
        artifact_store={artifact.content_hash: artifact},
    )

    # Policy has wrong baseline_config_ref
    policy = EvidencePolicy(
        policy_id="test-policy",
        version="1",
        null_family="paired_bounded_mean_betting",
        theta0=0.0,
        statistic="paired_advantage",
        support="[-1,1]",
        sampling_regime=_REGIME,
        baseline_config_ref=_FALLBACK_SHA,  # wrong — doesn't match live baseline config
        calibration_population_ref=artifact.content_hash,
        predictor_config_ref=_config_hash(predictor.config),
        executor_descriptor_ref=executor.credential(),
        evalue_transform="paired_wsr_betting",
    )
    claim = _make_claim(artifact)
    result = executor.execute(claim, _stub_cell(), policy, _make_ctx(), _make_fdr_test(claim.id))
    assert result.failure_reason is not None
    assert result.failure_reason.reason == "policy_mismatch"


# ---------------------------------------------------------------------------
# EvidenceExecutor Protocol conformance
# ---------------------------------------------------------------------------


def test_benchmark_executor_satisfies_protocol():
    from polymer_protocol.evidence_executor import EvidenceExecutor
    from polymer_claims.benchmark_capability import BenchmarkEvidenceExecutor

    artifact = _make_artifact_strong()
    store = {artifact.content_hash: artifact}
    ex = BenchmarkEvidenceExecutor(
        predictor=FixtureModelAdapter(),
        baseline_predictor=FixtureBaselineAdapter(),
        scorer=score_advantage,
        transform=paired_advantage_evalue,
        artifact_store=store,
    )
    assert isinstance(ex, EvidenceExecutor)


# ---------------------------------------------------------------------------
# No outcome filtering — negative advantage is still a success result
# ---------------------------------------------------------------------------


def test_no_outcome_filtering_all_ties_is_success():
    """All-tie W_i=0 results in low e_value but must not cause a FAILURE return."""
    from polymer_claims.benchmark_capability import BenchmarkEvidenceExecutor

    # Build examples where model = baseline for all (both wrong) so W_i = 0
    # Use a label class that neither adapter can predict
    n = 20
    examples = tuple(
        BenchmarkExample(
            example_id=f"e{i:04d}",
            features=(("idx", str(i)),),
            label="impossible_class_xyz",  # neither adapter ever predicts this
        )
        for i in range(n)
    )
    artifact = BenchmarkArtifact(
        examples=examples,
        target_population="test-population",
        sampling_regime=_REGIME,
        version="v1",
        sampling_seed=99,
        dgp_digest=_DGPDIGEST,
    )
    predictor = FixtureModelAdapter()
    baseline = FixtureBaselineAdapter()
    store = {artifact.content_hash: artifact}

    executor = BenchmarkEvidenceExecutor(
        predictor=predictor,
        baseline_predictor=baseline,
        scorer=score_advantage,
        transform=paired_advantage_evalue,
        artifact_store=store,
    )
    policy = _make_policy(artifact, predictor, baseline, executor_descriptor_ref=executor.credential())
    claim = _make_claim(artifact)
    result = executor.execute(claim, _stub_cell(), policy, _make_ctx(), _make_fdr_test(claim.id))

    # Should be SUCCESS even with low/zero e_value (no outcome filtering)
    assert result.failure_reason is None
    assert result.e_value is not None
    assert result.e_value >= 0.0
