"""Tests for EvidenceExecution state validator, ExecutionFailure, EvidenceExecutor Protocol,
and EvidenceRuntime dataclass.

PROTOCOL-TEST PURITY: no polymer_claims import.
"""
from __future__ import annotations

import dataclasses
import math

import pytest
from pydantic import ValidationError

from polymer_grammar.evaluate import EvaluationResult, ExecValue, VerifiedEvaluation
from polymer_grammar.licensing import LicenseRoute, MaterializationContext, SatisfactionVerdict
from polymer_grammar.verification_policy import EvidenceLicensingInfo, EvidenceProvenance
from polymer_protocol.corpus import ExecRecord
from polymer_protocol.evidence_executor import (
    EvidenceExecution,
    EvidenceExecutor,
    EvidenceRuntime,
    ExecutionFailure,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_HEX64 = "b" * 64
_SHA = f"sha256:{_HEX64}"
_BENCH = f"bench:sha256:{_HEX64}"
_CLAIM_ID = "claim-xyz-001"


def _mat() -> MaterializationContext:
    return MaterializationContext(id="m1", api_version="1.0", data_version="db@2026")


def _provenance(claim_id: str = _CLAIM_ID, e_value: float = 5.0) -> EvidenceProvenance:
    return EvidenceProvenance(
        claim_id=claim_id,
        executor_descriptor_ref=_SHA,
        evidence_policy_ref=_SHA,
        benchmark_ref=_BENCH,
        baseline_config_ref=_SHA,
        baseline_predictions_ref=_SHA,
        predictor_config_ref=_SHA,
        capability_descriptor_ref=_SHA,
        observed_advantage=0.1,
        theta0=0.5,
        e_value=e_value,
        execution_contract_digest=_SHA,
        fdr_test_index=1,
        alpha_allocated=0.05,
    )


def _licensing_info(claim_id: str = _CLAIM_ID) -> EvidenceLicensingInfo:
    return EvidenceLicensingInfo(
        route=LicenseRoute.EVIDENCE_LICENSED,
        verification_standing="single_source_baseline",
        evidence_provenance=_provenance(claim_id=claim_id),
        materialization=_mat(),
    )


def _undetermined_result(status: str = "complete") -> EvaluationResult:
    return EvaluationResult(
        verdict=SatisfactionVerdict.UNDETERMINED,
        terminal=ExecValue(value=None),
        nodes=(),
        adapter_identity="test-adapter",
        status=status,  # type: ignore[arg-type]
    )


def _error_result() -> EvaluationResult:
    return EvaluationResult(
        verdict=SatisfactionVerdict.UNDETERMINED,
        terminal=ExecValue(value=None),
        nodes=(),
        adapter_identity="test-adapter",
        status="error",
    )


def _verified_eval_undetermined() -> VerifiedEvaluation:
    return VerifiedEvaluation(
        results=(_undetermined_result(),),
        agreement=False,
        satisfaction=None,
    )


def _exec_record(claim_id: str = _CLAIM_ID) -> ExecRecord:
    return ExecRecord(
        claim_id=claim_id,
        evaluation=_verified_eval_undetermined(),
    )


# ---------------------------------------------------------------------------
# SUCCESS path
# ---------------------------------------------------------------------------


def test_success_valid():
    """A well-formed SUCCESS EvidenceExecution passes validation."""
    ee = EvidenceExecution(
        record=_exec_record(),
        e_value=5.0,
        licensing_info=_licensing_info(),
    )
    assert ee.failure_reason is None
    assert ee.e_value == 5.0


def test_success_inf_e_value_allowed():
    """+inf is allowed as an e_value (one-sided test with infinite evidence)."""
    ee = EvidenceExecution(
        record=_exec_record(),
        e_value=float("inf"),
        licensing_info=_licensing_info(),
    )
    assert math.isinf(ee.e_value)  # type: ignore[arg-type]


def test_success_zero_e_value_allowed():
    """e_value == 0 is allowed."""
    ee = EvidenceExecution(
        record=_exec_record(),
        e_value=0.0,
        licensing_info=_licensing_info(),
    )
    assert ee.e_value == 0.0


# ---------------------------------------------------------------------------
# SUCCESS path — rejection cases
# ---------------------------------------------------------------------------


def test_success_rejects_missing_e_value():
    """SUCCESS with e_value=None must fail."""
    with pytest.raises(ValidationError):
        EvidenceExecution(
            record=_exec_record(),
            e_value=None,
            licensing_info=_licensing_info(),
        )


def test_success_rejects_missing_licensing_info():
    """SUCCESS with licensing_info=None must fail."""
    with pytest.raises(ValidationError):
        EvidenceExecution(
            record=_exec_record(),
            e_value=5.0,
            licensing_info=None,
        )


def test_success_rejects_nan_e_value():
    """NaN e_value must be rejected."""
    with pytest.raises(ValidationError):
        EvidenceExecution(
            record=_exec_record(),
            e_value=float("nan"),
            licensing_info=_licensing_info(),
        )


def test_success_rejects_negative_e_value():
    """Negative e_value must be rejected."""
    with pytest.raises(ValidationError):
        EvidenceExecution(
            record=_exec_record(),
            e_value=-0.1,
            licensing_info=_licensing_info(),
        )


def test_success_rejects_claim_id_mismatch():
    """record.claim_id must match licensing_info.evidence_provenance.claim_id."""
    with pytest.raises(ValidationError):
        EvidenceExecution(
            record=_exec_record(claim_id="claim-A"),
            e_value=5.0,
            licensing_info=_licensing_info(claim_id="claim-B"),
        )


def test_success_rejects_satisfied_verdict():
    """SUCCESS path requires UNDETERMINED verdict, not SATISFIED."""
    satisfied_result = EvaluationResult(
        verdict=SatisfactionVerdict.SATISFIED,
        terminal=ExecValue(value=1.0),
        nodes=(),
        adapter_identity="test-adapter",
        status="complete",
    )
    # satisfaction must be None for success
    ve = VerifiedEvaluation(
        results=(satisfied_result,),
        agreement=True,
        satisfaction=None,
    )
    record = ExecRecord(claim_id=_CLAIM_ID, evaluation=ve)
    with pytest.raises(ValidationError):
        EvidenceExecution(record=record, e_value=5.0, licensing_info=_licensing_info())


def test_success_rejects_satisfaction_set():
    """satisfaction must be None in the SUCCESS path."""
    from polymer_grammar.licensing import Satisfaction  # noqa: PLC0415 — local import for test isolation

    satisfaction = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=_mat())
    ve = VerifiedEvaluation(
        results=(_undetermined_result(),),
        agreement=True,
        satisfaction=satisfaction,
    )
    record = ExecRecord(claim_id=_CLAIM_ID, evaluation=ve)
    with pytest.raises(ValidationError):
        EvidenceExecution(record=record, e_value=5.0, licensing_info=_licensing_info())


def test_success_rejects_multiple_results():
    """SUCCESS path requires EXACTLY one result."""
    ve = VerifiedEvaluation(
        results=(_undetermined_result(), _undetermined_result()),
        agreement=False,
        satisfaction=None,
    )
    record = ExecRecord(claim_id=_CLAIM_ID, evaluation=ve)
    with pytest.raises(ValidationError):
        EvidenceExecution(record=record, e_value=5.0, licensing_info=_licensing_info())


# ---------------------------------------------------------------------------
# FAILURE path
# ---------------------------------------------------------------------------


def _failure() -> ExecutionFailure:
    return ExecutionFailure(
        reason="predictor_error",
        stage="execution",
        detail="adapter raised RuntimeError",
    )


def _exec_record_error() -> ExecRecord:
    ve = VerifiedEvaluation(
        results=(_error_result(),),
        agreement=False,
        satisfaction=None,
    )
    return ExecRecord(claim_id=_CLAIM_ID, evaluation=ve)


def test_failure_valid():
    """A well-formed FAILURE EvidenceExecution passes validation."""
    ee = EvidenceExecution(
        record=_exec_record_error(),
        failure_reason=_failure(),
    )
    assert ee.e_value is None
    assert ee.licensing_info is None


def test_failure_rejects_e_value_set():
    """FAILURE with an e_value set must fail."""
    with pytest.raises(ValidationError):
        EvidenceExecution(
            record=_exec_record_error(),
            failure_reason=_failure(),
            e_value=1.0,
        )


def test_failure_rejects_licensing_info_set():
    """FAILURE with licensing_info set must fail."""
    with pytest.raises(ValidationError):
        EvidenceExecution(
            record=_exec_record_error(),
            failure_reason=_failure(),
            licensing_info=_licensing_info(),
        )


def test_failure_rejects_non_error_status():
    """FAILURE path requires result status=='error'."""
    ve = VerifiedEvaluation(
        results=(_undetermined_result(status="complete"),),
        agreement=False,
        satisfaction=None,
    )
    record = ExecRecord(claim_id=_CLAIM_ID, evaluation=ve)
    with pytest.raises(ValidationError):
        EvidenceExecution(
            record=record,
            failure_reason=_failure(),
        )


def test_failure_rejects_terminal_value_set():
    """FAILURE path requires terminal.value is None."""
    result_with_value = EvaluationResult(
        verdict=SatisfactionVerdict.UNDETERMINED,
        terminal=ExecValue(value=42.0),
        nodes=(),
        adapter_identity="test-adapter",
        status="error",
    )
    ve = VerifiedEvaluation(
        results=(result_with_value,),
        agreement=False,
        satisfaction=None,
    )
    record = ExecRecord(claim_id=_CLAIM_ID, evaluation=ve)
    with pytest.raises(ValidationError):
        EvidenceExecution(record=record, failure_reason=_failure())


# ---------------------------------------------------------------------------
# ExecutionFailure — model validation
# ---------------------------------------------------------------------------


def test_execution_failure_all_reasons():
    """All reason literals must be accepted."""
    reasons = [
        "empty", "malformed", "duplicate", "missing", "order_mismatch",
        "nonfinite_prediction", "out_of_support", "predictor_error",
        "policy_mismatch", "credential_mismatch", "digest_mismatch",
        "untrusted_executor",
    ]
    for reason in reasons:
        f = ExecutionFailure(reason=reason, stage="pre_dispatch")  # type: ignore[arg-type]
        assert f.reason == reason

    # Both stages accepted
    ExecutionFailure(reason="empty", stage="pre_dispatch")
    ExecutionFailure(reason="empty", stage="execution")


def test_execution_failure_detail_default():
    f = ExecutionFailure(reason="empty", stage="execution")
    assert f.detail == ""


# ---------------------------------------------------------------------------
# EvidenceExecutor Protocol
# ---------------------------------------------------------------------------


class _StubExecutor:
    """Minimal stub satisfying the EvidenceExecutor Protocol."""

    def credential(self) -> str:
        return "stub-executor-v1"

    def execute(self, claim, cell, policy, ctx, fdr_test) -> EvidenceExecution:
        return EvidenceExecution(
            record=_exec_record(),
            e_value=5.0,
            licensing_info=_licensing_info(),
        )


def test_stub_satisfies_protocol():
    """The stub executor satisfies the EvidenceExecutor structural protocol."""
    stub = _StubExecutor()
    assert isinstance(stub, EvidenceExecutor)


def test_protocol_credential_method():
    stub = _StubExecutor()
    assert stub.credential() == "stub-executor-v1"


def test_protocol_execute_returns_evidence_execution():
    stub = _StubExecutor()
    result = stub.execute(None, None, None, None, None)
    assert isinstance(result, EvidenceExecution)


# ---------------------------------------------------------------------------
# EvidenceRuntime dataclass
# ---------------------------------------------------------------------------


def test_evidence_runtime_is_dataclass():
    """EvidenceRuntime must be a plain frozen dataclass, not a _Model."""
    assert dataclasses.is_dataclass(EvidenceRuntime)


def test_evidence_runtime_not_pydantic():
    """EvidenceRuntime must not be a pydantic BaseModel."""
    from pydantic import BaseModel

    assert not issubclass(EvidenceRuntime, BaseModel)


def test_evidence_runtime_frozen():
    """EvidenceRuntime must be frozen (immutable)."""
    from polymer_grammar.capability import CapabilityRegistry
    from polymer_grammar.evidence_policy import EvidencePolicyRegistry
    from polymer_grammar.executor_credential import (
        ExecutorDescriptorRegistry,
        ExecutorTrustRegistry,
    )

    rt = EvidenceRuntime(
        capability_registry=CapabilityRegistry(),
        evidence_policy_registry=EvidencePolicyRegistry(),
        executor_descriptor_registry=ExecutorDescriptorRegistry(),
        executor_trust_registry=ExecutorTrustRegistry(),
        executor=_StubExecutor(),
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        rt.executor = _StubExecutor()  # type: ignore[misc]


def test_evidence_runtime_fields():
    """EvidenceRuntime must have the correct fields."""
    fields = {f.name for f in dataclasses.fields(EvidenceRuntime)}
    assert fields == {
        "capability_registry",
        "evidence_policy_registry",
        "executor_descriptor_registry",
        "executor_trust_registry",
        "executor",
    }
