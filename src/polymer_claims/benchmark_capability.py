"""BenchmarkEvidenceExecutor — umbrella EvidenceExecutor for V2.0 evidence-licensed
capability (benchmark pathway).

This module is the integration linchpin of Phase 1a: it wires together the benchmark
adapter, scorer, e-value transform, and grammar types into a single EvidenceExecutor
implementation that satisfies the polymer_protocol Protocol.

Umbrella-side: numpy is allowed here.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

from polymer_grammar.evaluate import (
    EvaluationResult,
    ExecValue,
    VerifiedEvaluation,
)
from polymer_grammar.executor_credential import Component, ExecutorDescriptor
from polymer_grammar.licensing import LicenseRoute, SatisfactionVerdict
from polymer_grammar.operations import DataHandle
from polymer_grammar.verification_policy import (
    EvidenceLicensingInfo,
    EvidenceProvenance,
    ExecutionContract,
)
from polymer_protocol.corpus import ExecRecord
from polymer_protocol.evidence_executor import EvidenceExecution, ExecutionFailure

from ._hashing import canonical_sha256
from .adapter_identity import implementation_hash_for_callable
from .benchmark_adapter import BenchmarkAdapter, BenchmarkArtifact
from .benchmark_evidence import PredictionVector, ScoringError

__all__ = ["BenchmarkEvidenceExecutor", "BenchmarkKit", "build_benchmark_kit", "EVAL_BENCHMARK_ADVANTAGE_CELL"]

_EXECUTOR_VERSION = "1.0"


def _config_hash(config: dict) -> str:
    """Canonical sha256 of an adapter's config dict."""
    return canonical_sha256(config)


def _fn_config_hash() -> str:
    """Config hash for pure-function components (no configurable state)."""
    return canonical_sha256({})


def _fn_identity(fn: object) -> str:
    """Stable identity string for a pure function (its qualname)."""
    return getattr(fn, "__qualname__", repr(fn))


def _make_failure_record(
    claim_id: str,
    adapter_identity: str,
) -> ExecRecord:
    """Build an ExecRecord for the FAILURE path (status='error', terminal=None)."""
    return ExecRecord(
        claim_id=claim_id,
        evaluation=VerifiedEvaluation(
            results=(
                EvaluationResult(
                    verdict=SatisfactionVerdict.UNDETERMINED,
                    terminal=ExecValue(value=None),
                    nodes=(),
                    adapter_identity=adapter_identity,
                    status="error",
                ),
            ),
            agreement=True,
            satisfaction=None,
        ),
    )


def _failure(
    claim_id: str,
    adapter_identity: str,
    reason: str,
    detail: str = "",
) -> EvidenceExecution:
    """Return a failure EvidenceExecution with the given reason."""
    return EvidenceExecution(
        record=_make_failure_record(claim_id, adapter_identity),
        e_value=None,
        licensing_info=None,
        failure_reason=ExecutionFailure(
            stage="execution",
            reason=reason,  # type: ignore[arg-type]
            detail=detail,
        ),
    )


class BenchmarkEvidenceExecutor:
    """Concrete EvidenceExecutor for the benchmark (paired-advantage e-value) pathway.

    Implements the ``EvidenceExecutor`` structural Protocol from ``polymer_protocol``.

    Construction
    ------------
    ``artifact_store``
        A mapping from artifact ``content_hash`` (the bare ``sha256:<hex>`` string,
        *without* the ``bench:`` prefix) to ``BenchmarkArtifact``.  The executor
        resolves the calibration population by looking up
        ``policy.calibration_population_ref`` in this store.
    """

    def __init__(
        self,
        *,
        predictor: BenchmarkAdapter,
        baseline_predictor: BenchmarkAdapter,
        scorer: Callable,
        transform: Callable,
        artifact_store: Mapping[str, BenchmarkArtifact],
    ) -> None:
        self._predictor = predictor
        self._baseline = baseline_predictor
        self._scorer = scorer
        self._transform = transform
        self._store = artifact_store

    # ------------------------------------------------------------------
    # credential()
    # ------------------------------------------------------------------

    def credential(self) -> str:
        """Recompute the live ExecutorDescriptor and return its content_hash.

        The descriptor is built from four Component objects — one per canonical
        role — using ``implementation_hash_for_callable`` over each component's
        executable and ``canonical_sha256`` over each component's config.
        """
        descriptor = ExecutorDescriptor(
            components=(
                Component(
                    role="predictor",
                    identity=self._predictor.identity,
                    implementation_hash=implementation_hash_for_callable(
                        self._predictor.predict
                    ),
                    config_hash=_config_hash(self._predictor.config),
                ),
                Component(
                    role="baseline_predictor",
                    identity=self._baseline.identity,
                    implementation_hash=implementation_hash_for_callable(
                        self._baseline.predict
                    ),
                    config_hash=_config_hash(self._baseline.config),
                ),
                Component(
                    role="scorer",
                    identity=_fn_identity(self._scorer),
                    implementation_hash=implementation_hash_for_callable(self._scorer),
                    config_hash=_fn_config_hash(),
                ),
                Component(
                    role="evidence_transform",
                    identity=_fn_identity(self._transform),
                    implementation_hash=implementation_hash_for_callable(self._transform),
                    config_hash=_fn_config_hash(),
                ),
            ),
            version=_EXECUTOR_VERSION,
        )
        return descriptor.content_hash

    # ------------------------------------------------------------------
    # execute()
    # ------------------------------------------------------------------

    def execute(
        self,
        claim: Any,
        cell: Any,
        policy: Any,
        ctx: Any,
        fdr_test: Any,
    ) -> EvidenceExecution:
        """Run evidence computation and return a complete EvidenceExecution.

        Steps
        -----
        1. Resolve the BenchmarkArtifact from the store.
        2. Verify the chain links (digest + policy config refs).
        3. Obtain predictions from both adapters.
        4. Score and compute the e-value.
        5. Build and return the EvidenceExecution.
        """
        live_credential = self.credential()
        claim_id: str = claim.id

        # ------------------------------------------------------------------
        # Step 1 — resolve the artifact
        # ------------------------------------------------------------------
        artifact_key: str = policy.calibration_population_ref  # sha256:<hex>
        artifact: BenchmarkArtifact | None = self._store.get(artifact_key)
        if artifact is None:
            return _failure(
                claim_id,
                live_credential,
                "digest_mismatch",
                f"artifact {artifact_key!r} not found in store",
            )

        # ------------------------------------------------------------------
        # Step 2 — verify chain links
        # ------------------------------------------------------------------

        # 2a. Claim's terminal DataHandle ref must match the artifact
        try:
            terminal_node = claim.evaluation_plan.graph.nodes[0]
            data_handle: DataHandle = terminal_node.inputs[0]
            claim_data_ref: str = data_handle.ref
        except (AttributeError, IndexError, TypeError) as exc:
            return _failure(
                claim_id,
                live_credential,
                "digest_mismatch",
                f"could not read DataHandle ref from claim: {exc}",
            )

        expected_data_ref = "bench:" + policy.calibration_population_ref
        if claim_data_ref != expected_data_ref or claim_data_ref != artifact.ref:
            return _failure(
                claim_id,
                live_credential,
                "digest_mismatch",
                f"claim DataHandle.ref {claim_data_ref!r} != expected {expected_data_ref!r}",
            )

        # 2b. Policy baseline_config_ref must match the live baseline config
        live_baseline_config_hash = _config_hash(self._baseline.config)
        if policy.baseline_config_ref != live_baseline_config_hash:
            return _failure(
                claim_id,
                live_credential,
                "policy_mismatch",
                (
                    f"policy.baseline_config_ref {policy.baseline_config_ref!r} "
                    f"!= live {live_baseline_config_hash!r}"
                ),
            )

        # 2c. Policy predictor_config_ref must match the live predictor config
        live_predictor_config_hash = _config_hash(self._predictor.config)
        if policy.predictor_config_ref != live_predictor_config_hash:
            return _failure(
                claim_id,
                live_credential,
                "policy_mismatch",
                (
                    f"policy.predictor_config_ref {policy.predictor_config_ref!r} "
                    f"!= live {live_predictor_config_hash!r}"
                ),
            )

        # ------------------------------------------------------------------
        # Step 3 — predict (label-free: adapters receive full examples but
        #           MUST derive predictions only from features/ids)
        # ------------------------------------------------------------------
        model_pv: PredictionVector = self._predictor.predict(artifact.examples)
        baseline_pv: PredictionVector = self._baseline.predict(artifact.examples)

        # ------------------------------------------------------------------
        # Step 4 — score and compute e-value
        # ------------------------------------------------------------------
        order = [ex.example_id for ex in artifact.examples]
        labels = {ex.example_id: ex.label for ex in artifact.examples}

        try:
            W = self._scorer(model_pv, baseline_pv, labels=labels, order=order)
        except ScoringError as exc:
            msg = str(exc)
            if "order" in msg.lower() or "sequence" in msg.lower():
                reason = "order_mismatch"
            elif "missing" in msg.lower():
                reason = "missing"
            elif "duplicate" in msg.lower():
                reason = "duplicate"
            else:
                reason = "order_mismatch"
            return _failure(claim_id, live_credential, reason, msg)

        arr = np.asarray(W, dtype=float)
        # observed_advantage = mean(model_correct) - mean(baseline_correct)
        # = mean(W_i) since W_i = 1(model) - 1(baseline)
        observed_advantage = float(np.mean(arr))

        e_value: float = self._transform(W, theta0=policy.theta0)

        # ------------------------------------------------------------------
        # Step 5 — build provenance, licensing info, and record
        # ------------------------------------------------------------------

        # Compute execution_contract_digest from the ExecutionContract
        execution_contract = ExecutionContract(
            capability_id=getattr(cell, "capability_id", "benchmark"),
            capability_version=getattr(cell, "capability_version", "1.0"),
            evidence_policy_ref=policy.content_hash,
            capability_descriptor_ref=cell.content_hash,
        )
        execution_contract_digest = canonical_sha256(
            execution_contract.model_dump(mode="json")
        )

        provenance = EvidenceProvenance(
            claim_id=claim_id,
            executor_descriptor_ref=policy.executor_descriptor_ref,
            evidence_policy_ref=policy.content_hash,
            benchmark_ref=artifact.ref,
            baseline_config_ref=policy.baseline_config_ref,
            baseline_predictions_ref=baseline_pv.ref,
            predictor_config_ref=policy.predictor_config_ref,
            capability_descriptor_ref=cell.content_hash,
            observed_advantage=observed_advantage,
            theta0=policy.theta0,
            e_value=e_value,
            execution_contract_digest=execution_contract_digest,
            fdr_test_index=fdr_test.index,
            alpha_allocated=fdr_test.alpha_allocated,
        )

        licensing_info = EvidenceLicensingInfo(
            route=LicenseRoute.EVIDENCE_LICENSED,
            verification_standing="single_source_baseline",
            evidence_provenance=provenance,
            materialization=ctx,
        )

        record = ExecRecord(
            claim_id=claim_id,
            evaluation=VerifiedEvaluation(
                results=(
                    EvaluationResult(
                        verdict=SatisfactionVerdict.UNDETERMINED,
                        terminal=ExecValue(value=observed_advantage),
                        nodes=(),
                        adapter_identity=policy.executor_descriptor_ref,
                        status="complete",
                    ),
                ),
                agreement=True,
                satisfaction=None,
            ),
        )

        return EvidenceExecution(
            record=record,
            e_value=e_value,
            licensing_info=licensing_info,
            failure_reason=None,
        )


# ---------------------------------------------------------------------------
# Task 16 — Consistent capability kit (used by registration + Task 19 e2e)
# ---------------------------------------------------------------------------

from typing import NamedTuple  # noqa: E402


class BenchmarkKit(NamedTuple):
    """All objects in the benchmark capability, built consistently by construction.

    ``descriptor.content_hash == executor.credential() == policy.executor_descriptor_ref``
    ``policy.calibration_population_ref == demo_benchmark.content_hash``
    """

    executor: "BenchmarkEvidenceExecutor"
    descriptor: "ExecutorDescriptor"
    policy: object  # EvidencePolicy (avoid forward-ref cycle)
    trust_entry: object  # ExecutorTrustEntry
    policy_registry: object  # EvidencePolicyRegistry
    descriptor_registry: object  # ExecutorDescriptorRegistry
    trust_registry: object  # ExecutorTrustRegistry
    demo_benchmark: "BenchmarkArtifact"
    cell: object  # CapabilityCell


def build_benchmark_kit() -> BenchmarkKit:
    """Build the full benchmark capability kit.

    All cross-object references are consistent by construction — no hand-coded hash strings.
    Safe to call multiple times (pure, deterministic).
    """
    from polymer_grammar.capability import (
        CapabilityCell, DataRefKind, OracleRequirement, SubjectRequirement,
    )
    from polymer_grammar.executor_credential import (
        ExecutorDescriptor as _ExecutorDescriptor,
        ExecutorDescriptorRegistry,
        ExecutorTrustEntry,
        ExecutorTrustRegistry,
    )
    from polymer_grammar.evidence_policy import EvidencePolicy, EvidencePolicyRegistry
    from polymer_grammar.operations import Comparator, MeasurementBasis, ProducedLeafSpec
    from polymer_grammar.pattern import PatternRef
    from polymer_grammar.sampling import SamplingRegime
    from polymer_grammar.verification_policy import VerificationPolicy

    from ._fixtures.benchmark_dgp import (
        DGPBaselineAdapter,
        DGPModelAdapter,
        TAU,
        build_demo_benchmark,
    )
    from .benchmark_evidence import paired_advantage_evalue, score_advantage

    # 1. Build demo benchmark (deterministic; content_hash is its calibration_population_ref)
    demo_benchmark = build_demo_benchmark()

    # 2. Build adapters.
    #    The model adapter gets the canonical Component identity "benchmark-model" so the
    #    descriptor's predictor role has that identity, which matches eligible_adapter_identities.
    #    The DGP config (MODEL_RULE_CONFIG) stays as-is; only the registry identity is overridden.
    model_adapter = DGPModelAdapter()
    model_adapter.identity = "benchmark-model"  # canonical registry identity for eligibility
    baseline_adapter = DGPBaselineAdapter()

    # 3. Build executor (owns the components; credential() recomputes the descriptor hash)
    executor = BenchmarkEvidenceExecutor(
        predictor=model_adapter,
        baseline_predictor=baseline_adapter,
        scorer=score_advantage,
        transform=paired_advantage_evalue,
        artifact_store={demo_benchmark.content_hash: demo_benchmark},
    )

    # 4. Build the ExecutorDescriptor with the SAME components the executor uses internally,
    #    so that descriptor.content_hash == executor.credential() by construction.
    descriptor = _ExecutorDescriptor(
        components=(
            Component(
                role="predictor",
                identity=model_adapter.identity,  # "benchmark-model"
                implementation_hash=implementation_hash_for_callable(model_adapter.predict),
                config_hash=_config_hash(model_adapter.config),
            ),
            Component(
                role="baseline_predictor",
                identity=baseline_adapter.identity,
                implementation_hash=implementation_hash_for_callable(baseline_adapter.predict),
                config_hash=_config_hash(baseline_adapter.config),
            ),
            Component(
                role="scorer",
                identity=_fn_identity(score_advantage),
                implementation_hash=implementation_hash_for_callable(score_advantage),
                config_hash=_fn_config_hash(),
            ),
            Component(
                role="evidence_transform",
                identity=_fn_identity(paired_advantage_evalue),
                implementation_hash=implementation_hash_for_callable(paired_advantage_evalue),
                config_hash=_fn_config_hash(),
            ),
        ),
        version=_EXECUTOR_VERSION,
    )
    # Hard invariant: must match at construction time or something changed.
    assert descriptor.content_hash == executor.credential(), (
        f"Kit invariant violated: descriptor.content_hash {descriptor.content_hash!r} "
        f"!= executor.credential() {executor.credential()!r}"
    )

    # 5. Build EvidencePolicy — all refs are live-computed, no hand-coded hashes.
    policy = EvidencePolicy(
        policy_id="benchmark-advantage-v1",
        version="v1",
        null_family="paired_bounded_mean_betting",
        theta0=TAU,
        statistic="paired_mean_increment",
        support="[-1,1]",
        sampling_regime=SamplingRegime.IID_EXAMPLES,
        baseline_config_ref=_config_hash(baseline_adapter.config),
        calibration_population_ref=demo_benchmark.content_hash,
        predictor_config_ref=_config_hash(model_adapter.config),
        executor_descriptor_ref=descriptor.content_hash,
        evalue_transform="paired_wsr_betting",
    )

    # 6. ExecutorTrustEntry: trust the descriptor we just built.
    trust_entry = ExecutorTrustEntry(
        descriptor_ref=descriptor.content_hash,
        owner="polymer-claims-v1",
        trusted=True,
        version="v1",
    )

    # 7. Registries
    policy_registry = EvidencePolicyRegistry(policies=(policy,))
    descriptor_registry = ExecutorDescriptorRegistry(descriptors=(descriptor,))
    trust_registry = ExecutorTrustRegistry(entries=(trust_entry,))

    # 8. CapabilityCell (evidence_policy_ref = policy.content_hash, live-computed)
    _q = ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED)
    cell = CapabilityCell(
        capability_id="eval::benchmark_advantage",
        capability_version="v1",
        operation_impl="eval::benchmark_advantage",
        title="model-vs-baseline benchmark advantage",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        subject=SubjectRequirement(mode="forbidden"),
        param_schema=(),
        produced=_q,
        allowed_comparators=(Comparator.GT,),
        eligible_adapter_identities=("benchmark-model",),
        min_executing_adapters=1,
        oracle=OracleRequirement(default_oracle_id="benchmark_eval_apparatus", required=True),
        data_ref_kind=DataRefKind.BENCHMARK,
        claim_leaf_kinds=("categorical",),
        criterion_target="threshold",
        verification_policy=VerificationPolicy(
            execution="single",
            result_rule="evalue_discovery",
            independence_requirement="baseline_ground_truth",
            evidence_policy_ref=policy.content_hash,
            min_adapters=1,
        ),
    )

    return BenchmarkKit(
        executor=executor,
        descriptor=descriptor,
        policy=policy,
        trust_entry=trust_entry,
        policy_registry=policy_registry,
        descriptor_registry=descriptor_registry,
        trust_registry=trust_registry,
        demo_benchmark=demo_benchmark,
        cell=cell,
    )


# Module-level instances (built once; deterministic)
_BENCHMARK_KIT: BenchmarkKit = build_benchmark_kit()
EVAL_BENCHMARK_ADVANTAGE_CELL = _BENCHMARK_KIT.cell
