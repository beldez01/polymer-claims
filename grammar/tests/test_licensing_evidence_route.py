"""Tests for the EVIDENCE_LICENSED route on Licensing (Task 8)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)
from polymer_grammar.verification_policy import EvidenceProvenance

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HEX64 = "a" * 64
_SHA = f"sha256:{_HEX64}"
_BENCH = f"bench:sha256:{_HEX64}"


def _m(id_: str = "m1") -> MaterializationContext:
    return MaterializationContext(id=id_, api_version="0.9.x", data_version="db@2026-06-01")


def _sat(id_: str = "m1") -> Satisfaction:
    return Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=_m(id_))


def _provenance() -> EvidenceProvenance:
    return EvidenceProvenance(
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


def _evidence_licensing() -> Licensing:
    return Licensing(
        route=LicenseRoute.EVIDENCE_LICENSED,
        satisfactions=(_sat(),),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
        independence_tier=None,
        verification_standing="single_source_baseline",
        evidence_provenance=_provenance(),
    )


# ---------------------------------------------------------------------------
# EVIDENCE_LICENSED route — happy path
# ---------------------------------------------------------------------------


def test_evidence_licensed_enum_member_exists():
    assert LicenseRoute.EVIDENCE_LICENSED.value == "evidence_licensed"


def test_evidence_licensed_licensing_builds():
    lic = _evidence_licensing()
    assert lic.route == LicenseRoute.EVIDENCE_LICENSED
    assert lic.independence_tier is None
    assert lic.verification_standing == "single_source_baseline"
    assert isinstance(lic.evidence_provenance, EvidenceProvenance)


def test_evidence_licensed_round_trip_json():
    """JSON dump → model_validate produces an identical object."""
    lic = _evidence_licensing()
    dumped = lic.model_dump(mode="json")
    # Both new fields should be present in the dump for an evidence-licensed record
    assert "verification_standing" in dumped
    assert "evidence_provenance" in dumped
    rebuilt = Licensing.model_validate(dumped)
    assert rebuilt == lic


def test_evidence_licensed_independence_tier_none_is_serialized():
    """independence_tier=None IS present in the serialized output (not dropped)."""
    lic = _evidence_licensing()
    dumped = lic.model_dump(mode="json")
    assert "independence_tier" in dumped
    assert dumped["independence_tier"] is None


# ---------------------------------------------------------------------------
# EVIDENCE_LICENSED route — validator errors
# ---------------------------------------------------------------------------


def test_evidence_licensed_missing_verification_standing_raises():
    with pytest.raises(ValidationError, match="verification_standing"):
        Licensing(
            route=LicenseRoute.EVIDENCE_LICENSED,
            satisfactions=(_sat(),),
            rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            independence_tier=None,
            # verification_standing omitted
            evidence_provenance=_provenance(),
        )


def test_evidence_licensed_missing_evidence_provenance_raises():
    with pytest.raises(ValidationError, match="evidence_provenance"):
        Licensing(
            route=LicenseRoute.EVIDENCE_LICENSED,
            satisfactions=(_sat(),),
            rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            independence_tier=None,
            verification_standing="single_source_baseline",
            # evidence_provenance omitted
        )


def test_severe_test_with_verification_standing_raises():
    with pytest.raises(ValidationError):
        Licensing(
            route=LicenseRoute.SEVERE_TEST,
            satisfactions=(_sat(),),
            rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            verification_standing="single_source_baseline",
        )


def test_severe_test_with_evidence_provenance_raises():
    with pytest.raises(ValidationError):
        Licensing(
            route=LicenseRoute.SEVERE_TEST,
            satisfactions=(_sat(),),
            rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            evidence_provenance=_provenance(),
        )


# ---------------------------------------------------------------------------
# Existing invariants still hold on EVIDENCE_LICENSED route
# ---------------------------------------------------------------------------


def test_evidence_licensed_empty_satisfactions_still_rejected():
    with pytest.raises(ValidationError, match=">=1 satisfaction"):
        Licensing(
            route=LicenseRoute.EVIDENCE_LICENSED,
            satisfactions=(),
            rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            independence_tier=None,
            verification_standing="single_source_baseline",
            evidence_provenance=_provenance(),
        )


def test_evidence_licensed_non_satisfied_verdict_still_rejected():
    with pytest.raises(ValidationError):
        Licensing(
            route=LicenseRoute.EVIDENCE_LICENSED,
            satisfactions=(
                Satisfaction(
                    verdict=SatisfactionVerdict.UNDETERMINED,
                    materialization=_m(),
                ),
            ),
            rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            independence_tier=None,
            verification_standing="single_source_baseline",
            evidence_provenance=_provenance(),
        )
