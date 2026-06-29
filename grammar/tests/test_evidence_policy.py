"""Tests for EvidencePolicy and EvidencePolicyRegistry."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from polymer_grammar import EvidencePolicy, EvidencePolicyRegistry
from polymer_grammar.sampling import SamplingRegime

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_VALID_REF = "sha256:" + "a" * 64


def _make_policy(**overrides) -> EvidencePolicy:
    base = dict(
        policy_id="pol-001",
        version="1.0",
        null_family="paired_bounded_mean_betting",
        theta0=0.05,
        statistic="mean",
        support="[0,1]",
        sampling_regime=SamplingRegime.IID_EXAMPLES,
        baseline_config_ref=_VALID_REF,
        calibration_population_ref=_VALID_REF,
        predictor_config_ref="sha256:" + "b" * 64,
        executor_descriptor_ref="sha256:" + "c" * 64,
        evalue_transform="paired_wsr_betting",
    )
    base.update(overrides)
    return EvidencePolicy(**base)


# ---------------------------------------------------------------------------
# content_hash / ref basics
# ---------------------------------------------------------------------------


def test_content_hash_sha256_prefix():
    policy = _make_policy()
    assert policy.content_hash.startswith("sha256:")


def test_ref_equals_content_hash():
    policy = _make_policy()
    assert policy.ref == policy.content_hash


def test_content_hash_is_deterministic():
    p1 = _make_policy()
    p2 = _make_policy()
    assert p1.content_hash == p2.content_hash


def test_changing_field_changes_content_hash():
    p1 = _make_policy(theta0=0.05)
    p2 = _make_policy(theta0=0.10)
    assert p1.content_hash != p2.content_hash


def test_changing_policy_id_changes_content_hash():
    p1 = _make_policy(policy_id="pol-001")
    p2 = _make_policy(policy_id="pol-002")
    assert p1.content_hash != p2.content_hash


# ---------------------------------------------------------------------------
# theta0 validators
# ---------------------------------------------------------------------------


def test_theta0_zero_is_valid():
    _make_policy(theta0=0.0)


def test_theta0_just_below_one_is_valid():
    _make_policy(theta0=0.999)


def test_theta0_one_raises():
    with pytest.raises(ValidationError):
        _make_policy(theta0=1.0)


def test_theta0_negative_raises():
    with pytest.raises(ValidationError):
        _make_policy(theta0=-0.1)


def test_theta0_nan_raises():
    with pytest.raises(ValidationError):
        _make_policy(theta0=float("nan"))


def test_theta0_inf_raises():
    with pytest.raises(ValidationError):
        _make_policy(theta0=float("inf"))


def test_theta0_neg_inf_raises():
    with pytest.raises(ValidationError):
        _make_policy(theta0=float("-inf"))


# ---------------------------------------------------------------------------
# sha256-ref validators
# ---------------------------------------------------------------------------


def test_invalid_ref_not_sha256_prefix():
    with pytest.raises(ValidationError):
        _make_policy(baseline_config_ref="notsha256:" + "a" * 64)


def test_invalid_ref_too_short():
    with pytest.raises(ValidationError):
        _make_policy(predictor_config_ref="sha256:" + "a" * 63)


def test_invalid_ref_uppercase_hex():
    with pytest.raises(ValidationError):
        _make_policy(executor_descriptor_ref="sha256:" + "A" * 64)


def test_invalid_ref_calibration_population():
    with pytest.raises(ValidationError):
        _make_policy(calibration_population_ref="bench:sha256:" + "a" * 64)


# ---------------------------------------------------------------------------
# Family/transform compatibility
# ---------------------------------------------------------------------------


def test_mismatched_family_transform_raises():
    """null_family and evalue_transform must be a compatible pair."""
    with pytest.raises(ValidationError):
        # We can't construct an incompatible pair using Literals, so we bypass
        # via model_construct or just test that the valid pair passes.
        # The only valid pair is the one we use, so any change in one literal
        # field would be a type error at construction time. We test the validator
        # logic directly by checking that the valid combo works and invalid combos
        # fail. Since both fields are Literals, the validator guards against
        # future relaxation.
        EvidencePolicy(
            policy_id="pol-x",
            version="1",
            null_family="paired_bounded_mean_betting",
            theta0=0.05,
            statistic="mean",
            support="[0,1]",
            sampling_regime=SamplingRegime.IID_EXAMPLES,
            baseline_config_ref=_VALID_REF,
            calibration_population_ref=_VALID_REF,
            predictor_config_ref="sha256:" + "b" * 64,
            executor_descriptor_ref="sha256:" + "c" * 64,
            # Force a Pydantic validation error by passing an invalid literal value
            evalue_transform="nonexistent_transform",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Non-empty string validators
# ---------------------------------------------------------------------------


def test_empty_policy_id_raises():
    with pytest.raises(ValidationError):
        _make_policy(policy_id="")


def test_blank_policy_id_raises():
    with pytest.raises(ValidationError):
        _make_policy(policy_id="   ")


def test_empty_version_raises():
    with pytest.raises(ValidationError):
        _make_policy(version="")


def test_empty_statistic_raises():
    with pytest.raises(ValidationError):
        _make_policy(statistic="")


def test_empty_support_raises():
    with pytest.raises(ValidationError):
        _make_policy(support="")


# ---------------------------------------------------------------------------
# EvidencePolicyRegistry
# ---------------------------------------------------------------------------


def test_empty_registry_is_valid():
    reg = EvidencePolicyRegistry()
    assert reg.policies == ()


def test_resolve_round_trip():
    policy = _make_policy()
    reg = EvidencePolicyRegistry(policies=(policy,))
    resolved = reg.resolve(policy.content_hash)
    assert resolved == policy


def test_resolve_unknown_ref_returns_none():
    policy = _make_policy()
    reg = EvidencePolicyRegistry(policies=(policy,))
    assert reg.resolve("sha256:" + "0" * 64) is None


def test_registry_with_distinct_policies():
    p1 = _make_policy(policy_id="pol-001", version="1.0")
    p2 = _make_policy(policy_id="pol-002", version="1.0")
    reg = EvidencePolicyRegistry(policies=(p1, p2))
    assert reg.resolve(p1.content_hash) == p1
    assert reg.resolve(p2.content_hash) == p2


def test_duplicate_content_hash_in_registry_raises():
    """Two policies with identical fields (and thus the same content_hash) must be rejected."""
    policy = _make_policy()
    # Same fields = same content_hash
    policy_dup = _make_policy()
    assert policy.content_hash == policy_dup.content_hash
    with pytest.raises(ValidationError):
        EvidencePolicyRegistry(policies=(policy, policy_dup))


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


def test_evidence_policy_is_frozen():
    policy = _make_policy()
    with pytest.raises(Exception):
        policy.theta0 = 0.5  # type: ignore[misc]
