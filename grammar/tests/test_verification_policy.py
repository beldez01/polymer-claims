"""Tests for VerificationPolicy, ExecutionContract, EvidenceProvenance, EvidenceLicensingInfo."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from polymer_grammar.licensing import LicenseRoute, MaterializationContext
from polymer_grammar.verification_policy import (
    EvidenceLicensingInfo,
    EvidenceProvenance,
    ExecutionContract,
    VerificationPolicy,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HEX64 = "a" * 64
_SHA = f"sha256:{_HEX64}"
_BENCH = f"bench:sha256:{_HEX64}"


def _valid_recompute() -> VerificationPolicy:
    return VerificationPolicy(
        execution="recompute_pair",
        result_rule="criterion",
        independence_requirement="implementation",
        evidence_policy_ref=None,
        min_adapters=2,
    )


def _valid_single() -> VerificationPolicy:
    return VerificationPolicy(
        execution="single",
        result_rule="evalue_discovery",
        independence_requirement="baseline_ground_truth",
        evidence_policy_ref=_SHA,
        min_adapters=1,
    )


def _valid_provenance(**overrides) -> dict:
    base = dict(
        claim_id="claim-001",
        executor_descriptor_ref=_SHA,
        evidence_policy_ref=_SHA,
        benchmark_ref=_BENCH,
        baseline_config_ref=_SHA,
        baseline_predictions_ref=_SHA,
        predictor_config_ref=_SHA,
        capability_descriptor_ref=_SHA,
        oracle_dossier_ref=None,
        observed_advantage=0.1,
        theta0=0.5,
        e_value=10.0,
        execution_contract_digest=_SHA,
        fdr_test_index=1,
        alpha_allocated=0.05,
    )
    base.update(overrides)
    return base


def _mat() -> MaterializationContext:
    return MaterializationContext(id="m1", api_version="0.9.x", data_version="db@2026")


# ---------------------------------------------------------------------------
# VerificationPolicy — mode validation
# ---------------------------------------------------------------------------


def test_recompute_pair_valid():
    vp = _valid_recompute()
    assert vp.execution == "recompute_pair"
    assert vp.min_adapters == 2


def test_single_valid():
    vp = _valid_single()
    assert vp.execution == "single"
    assert vp.min_adapters == 1


def test_single_with_result_rule_criterion_is_error():
    """single mode requires result_rule='evalue_discovery', not 'criterion'."""
    with pytest.raises(ValidationError):
        VerificationPolicy(
            execution="single",
            result_rule="criterion",
            independence_requirement="baseline_ground_truth",
            evidence_policy_ref=_SHA,
            min_adapters=1,
        )


def test_recompute_pair_with_evidence_policy_ref_set_is_error():
    """recompute_pair mode must have evidence_policy_ref=None."""
    with pytest.raises(ValidationError):
        VerificationPolicy(
            execution="recompute_pair",
            result_rule="criterion",
            independence_requirement="implementation",
            evidence_policy_ref=_SHA,
            min_adapters=2,
        )


def test_recompute_pair_wrong_result_rule_is_error():
    with pytest.raises(ValidationError):
        VerificationPolicy(
            execution="recompute_pair",
            result_rule="evalue_discovery",
            independence_requirement="implementation",
            evidence_policy_ref=None,
            min_adapters=2,
        )


def test_recompute_pair_wrong_independence_is_error():
    with pytest.raises(ValidationError):
        VerificationPolicy(
            execution="recompute_pair",
            result_rule="criterion",
            independence_requirement="baseline_ground_truth",
            evidence_policy_ref=None,
            min_adapters=2,
        )


def test_recompute_pair_wrong_min_adapters_is_error():
    with pytest.raises(ValidationError):
        VerificationPolicy(
            execution="recompute_pair",
            result_rule="criterion",
            independence_requirement="implementation",
            evidence_policy_ref=None,
            min_adapters=1,
        )


def test_single_missing_evidence_policy_ref_is_error():
    with pytest.raises(ValidationError):
        VerificationPolicy(
            execution="single",
            result_rule="evalue_discovery",
            independence_requirement="baseline_ground_truth",
            evidence_policy_ref=None,
            min_adapters=1,
        )


def test_single_bad_evidence_policy_ref_shape_is_error():
    with pytest.raises(ValidationError):
        VerificationPolicy(
            execution="single",
            result_rule="evalue_discovery",
            independence_requirement="baseline_ground_truth",
            evidence_policy_ref="not-a-sha256",
            min_adapters=1,
        )


def test_single_wrong_min_adapters_is_error():
    with pytest.raises(ValidationError):
        VerificationPolicy(
            execution="single",
            result_rule="evalue_discovery",
            independence_requirement="baseline_ground_truth",
            evidence_policy_ref=_SHA,
            min_adapters=2,
        )


# ---------------------------------------------------------------------------
# ExecutionContract
# ---------------------------------------------------------------------------


def test_execution_contract_valid():
    ec = ExecutionContract(
        capability_id="bio::dmp",
        capability_version="v1",
        evidence_policy_ref=_SHA,
        capability_descriptor_ref=_SHA,
    )
    assert ec.capability_id == "bio::dmp"


def test_execution_contract_empty_capability_id_is_error():
    with pytest.raises(ValidationError):
        ExecutionContract(
            capability_id="   ",
            capability_version="v1",
            evidence_policy_ref=_SHA,
            capability_descriptor_ref=_SHA,
        )


def test_execution_contract_bad_ref_is_error():
    with pytest.raises(ValidationError):
        ExecutionContract(
            capability_id="bio::dmp",
            capability_version="v1",
            evidence_policy_ref="not-sha256",
            capability_descriptor_ref=_SHA,
        )


# ---------------------------------------------------------------------------
# EvidenceProvenance — numeric invariants
# ---------------------------------------------------------------------------


def test_provenance_valid_round_trip():
    ep = EvidenceProvenance(**_valid_provenance())
    assert ep.claim_id == "claim-001"
    assert ep.e_value == 10.0


def test_provenance_e_value_negative_is_error():
    with pytest.raises(ValidationError):
        EvidenceProvenance(**_valid_provenance(e_value=-1.0))


def test_provenance_e_value_nan_is_error():
    with pytest.raises(ValidationError):
        EvidenceProvenance(**_valid_provenance(e_value=float("nan")))


def test_provenance_e_value_positive_infinity_is_ok():
    """Positive infinity is permitted — real n-DMP evidence can produce it."""
    ep = EvidenceProvenance(**_valid_provenance(e_value=float("inf")))
    assert ep.e_value == float("inf")


def test_provenance_alpha_allocated_zero_is_error():
    with pytest.raises(ValidationError):
        EvidenceProvenance(**_valid_provenance(alpha_allocated=0.0))


def test_provenance_alpha_allocated_one_is_ok():
    ep = EvidenceProvenance(**_valid_provenance(alpha_allocated=1.0))
    assert ep.alpha_allocated == 1.0


def test_provenance_observed_advantage_out_of_range_is_error():
    with pytest.raises(ValidationError):
        EvidenceProvenance(**_valid_provenance(observed_advantage=2.0))


def test_provenance_observed_advantage_minus_one_is_ok():
    ep = EvidenceProvenance(**_valid_provenance(observed_advantage=-1.0))
    assert ep.observed_advantage == -1.0


def test_provenance_empty_claim_id_is_error():
    with pytest.raises(ValidationError):
        EvidenceProvenance(**_valid_provenance(claim_id=""))


def test_provenance_fdr_test_index_zero_is_error():
    with pytest.raises(ValidationError):
        EvidenceProvenance(**_valid_provenance(fdr_test_index=0))


def test_provenance_theta0_one_is_error():
    with pytest.raises(ValidationError):
        EvidenceProvenance(**_valid_provenance(theta0=1.0))


def test_provenance_theta0_zero_is_ok():
    ep = EvidenceProvenance(**_valid_provenance(theta0=0.0))
    assert ep.theta0 == 0.0


def test_provenance_bad_benchmark_ref_is_error():
    with pytest.raises(ValidationError):
        EvidenceProvenance(**_valid_provenance(benchmark_ref=_SHA))  # missing bench: prefix


def test_provenance_oracle_dossier_ref_accepted_when_present():
    ep = EvidenceProvenance(**_valid_provenance(oracle_dossier_ref=_SHA))
    assert ep.oracle_dossier_ref == _SHA


# ---------------------------------------------------------------------------
# EvidenceLicensingInfo
# ---------------------------------------------------------------------------


def test_evidence_licensing_info_constructs():
    info = EvidenceLicensingInfo(
        route=LicenseRoute.SEVERE_TEST,
        verification_standing="single_source_baseline",
        evidence_provenance=EvidenceProvenance(**_valid_provenance()),
        materialization=_mat(),
    )
    assert info.route == LicenseRoute.SEVERE_TEST
    assert info.verification_standing == "single_source_baseline"


def test_evidence_licensing_info_rejects_wrong_standing():
    """verification_standing is a Literal — any other string must be rejected."""
    with pytest.raises(ValidationError):
        EvidenceLicensingInfo(
            route=LicenseRoute.SEVERE_TEST,
            verification_standing="multi_source",  # type: ignore[arg-type]
            evidence_provenance=EvidenceProvenance(**_valid_provenance()),
            materialization=_mat(),
        )


def test_evidence_licensing_info_all_existing_license_routes():
    """Constructs with every existing LicenseRoute member (EVIDENCE_LICENSED not yet added)."""
    for route in LicenseRoute:
        info = EvidenceLicensingInfo(
            route=route,
            verification_standing="single_source_baseline",
            evidence_provenance=EvidenceProvenance(**_valid_provenance()),
            materialization=_mat(),
        )
        assert info.route == route
