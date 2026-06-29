"""Backward-compatibility tests for Licensing serialization (Task 8).

A non-evidence Licensing's model_dump must be byte-identical in shape to the
pre-Task-8 output: no `verification_standing` or `evidence_provenance` keys.
"""
from __future__ import annotations

import json

from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)
from polymer_grammar.status import PendingReason


def _m(id_: str = "m1") -> MaterializationContext:
    return MaterializationContext(id=id_, api_version="0.9.x", data_version="db@2026-06-01")


def _sat(id_: str = "m1") -> Satisfaction:
    return Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=_m(id_))


def _non_evidence_licensing() -> Licensing:
    return Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(_sat(),),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
    )


# ---------------------------------------------------------------------------
# Compat: serializer omits-when-None correctly
# ---------------------------------------------------------------------------


def test_non_evidence_dump_contains_no_verification_standing_key():
    dumped = _non_evidence_licensing().model_dump(mode="json")
    assert "verification_standing" not in dumped, (
        f"verification_standing must not appear in a non-evidence dump; got: {list(dumped)}"
    )


def test_non_evidence_dump_contains_no_evidence_provenance_key():
    dumped = _non_evidence_licensing().model_dump(mode="json")
    assert "evidence_provenance" not in dumped, (
        f"evidence_provenance must not appear in a non-evidence dump; got: {list(dumped)}"
    )


def test_non_evidence_dump_python_mode_no_new_keys():
    """mode='python' (default) also omits the two new None fields."""
    dumped = _non_evidence_licensing().model_dump()
    assert "verification_standing" not in dumped
    assert "evidence_provenance" not in dumped


def test_non_evidence_dump_field_order_and_shape():
    """The JSON dump matches the pre-Task-8 field set exactly."""
    dumped = _non_evidence_licensing().model_dump(mode="json")
    expected_keys = {
        "route",
        "satisfactions",
        "rival_set_closure",
        "rivals_considered",
        "independence_tier",
        "severity_provenance",
        "shared_cause_overlap",
        "note",
    }
    assert set(dumped.keys()) == expected_keys, (
        f"key set mismatch: {set(dumped.keys())} != {expected_keys}"
    )


# ---------------------------------------------------------------------------
# Compat: historical JSON without new fields deserializes cleanly
# ---------------------------------------------------------------------------


def test_historical_json_without_new_fields_deserializes():
    """JSON produced before Task 8 (no verification_standing/evidence_provenance)
    must still parse into a valid Licensing."""
    historical = {
        "route": "severe_test",
        "satisfactions": [
            {
                "verdict": "satisfied",
                "materialization": {
                    "id": "m1",
                    "api_version": "0.9.x",
                    "data_version": "db@2026-06-01",
                    "note": None,
                    "semantic_run_id": None,
                    "profile_hash": None,
                    "dimnames_hash": None,
                    "shared_cause_factors": [],
                },
                "credential_ids": [],
            }
        ],
        "rival_set_closure": "open_acknowledged",
        "rivals_considered": [],
        "independence_tier": "reproduced",
        "severity_provenance": None,
        "shared_cause_overlap": None,
        "note": None,
    }
    lic = Licensing.model_validate(historical)
    assert lic.route == LicenseRoute.SEVERE_TEST
    assert lic.verification_standing is None
    assert lic.evidence_provenance is None


def test_historical_json_string_deserializes():
    """Same check via model_validate_json."""
    historical_json = json.dumps({
        "route": "severe_test",
        "satisfactions": [
            {
                "verdict": "satisfied",
                "materialization": {
                    "id": "m1",
                    "api_version": "0.9.x",
                    "data_version": "db@2026-06-01",
                    "note": None,
                    "semantic_run_id": None,
                    "profile_hash": None,
                    "dimnames_hash": None,
                    "shared_cause_factors": [],
                },
                "credential_ids": [],
            }
        ],
        "rival_set_closure": "open_acknowledged",
        "rivals_considered": [],
        "independence_tier": "reproduced",
        "severity_provenance": None,
        "shared_cause_overlap": None,
        "note": None,
    })
    lic = Licensing.model_validate_json(historical_json)
    assert lic.route == LicenseRoute.SEVERE_TEST
    assert lic.independence_tier.value == "reproduced"


# ---------------------------------------------------------------------------
# PendingReason.EXECUTION_ERROR
# ---------------------------------------------------------------------------


def test_execution_error_pending_reason_exists():
    assert PendingReason.EXECUTION_ERROR.value == "execution_error"


def test_execution_error_is_string_enum():
    assert isinstance(PendingReason.EXECUTION_ERROR, str)
    assert PendingReason.EXECUTION_ERROR == "execution_error"
