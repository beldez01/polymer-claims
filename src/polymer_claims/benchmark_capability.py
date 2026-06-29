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

__all__ = ["BenchmarkEvidenceExecutor"]

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
