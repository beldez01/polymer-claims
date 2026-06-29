"""EvidencePolicy — evidence-licensed capability descriptor (V2.0 spec).
Pure / numpy-free: grammar + stdlib only."""
from __future__ import annotations

import math
import re
from typing import Literal

from pydantic import model_validator

from .base import _Model
from .operations import _sha
from .sampling import SamplingRegime

_SHA256_REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

_FAMILY_TRANSFORM_PAIRS: frozenset[tuple[str, str]] = frozenset(
    [("paired_bounded_mean_betting", "paired_wsr_betting")]
)


class EvidencePolicy(_Model):
    """A versioned policy that governs evidence-based capability licensing."""

    policy_id: str
    version: str
    null_family: Literal["paired_bounded_mean_betting"]
    theta0: float
    statistic: str
    support: str
    sampling_regime: SamplingRegime
    baseline_config_ref: str
    calibration_population_ref: str
    predictor_config_ref: str
    executor_descriptor_ref: str
    evalue_transform: Literal["paired_wsr_betting"]

    @model_validator(mode="after")
    def _validate(self) -> EvidencePolicy:
        # Non-empty string fields
        for field_name, value in [
            ("policy_id", self.policy_id),
            ("version", self.version),
            ("statistic", self.statistic),
            ("support", self.support),
        ]:
            if not value.strip():
                raise ValueError(f"{field_name} must be nonempty")

        # sha256-ref-shaped *_ref fields
        for field_name, value in [
            ("baseline_config_ref", self.baseline_config_ref),
            ("calibration_population_ref", self.calibration_population_ref),
            ("predictor_config_ref", self.predictor_config_ref),
            ("executor_descriptor_ref", self.executor_descriptor_ref),
        ]:
            if not _SHA256_REF_RE.match(value):
                raise ValueError(
                    f"{field_name} must be 'sha256:<64 lowercase hex>', got {value!r}"
                )

        # theta0: finite and 0 <= theta0 < 1
        if not math.isfinite(self.theta0):
            raise ValueError(f"theta0 must be finite, got {self.theta0}")
        if not (0.0 <= self.theta0 < 1.0):
            raise ValueError(
                f"theta0 must satisfy 0 <= theta0 < 1, got {self.theta0}"
            )

        # null_family <-> evalue_transform compatibility
        pair = (self.null_family, self.evalue_transform)
        if pair not in _FAMILY_TRANSFORM_PAIRS:
            raise ValueError(
                f"null_family {self.null_family!r} is incompatible with "
                f"evalue_transform {self.evalue_transform!r}"
            )

        return self

    @property
    def content_hash(self) -> str:
        canonical = {
            "policy_id": self.policy_id,
            "version": self.version,
            "null_family": self.null_family,
            "theta0": self.theta0,
            "statistic": self.statistic,
            "support": self.support,
            "sampling_regime": self.sampling_regime.value,
            "baseline_config_ref": self.baseline_config_ref,
            "calibration_population_ref": self.calibration_population_ref,
            "predictor_config_ref": self.predictor_config_ref,
            "executor_descriptor_ref": self.executor_descriptor_ref,
            "evalue_transform": self.evalue_transform,
        }
        return "sha256:" + _sha(canonical)

    @property
    def ref(self) -> str:
        return self.content_hash


class EvidencePolicyRegistry(_Model):
    """Registry of EvidencePolicy objects; enforces unique content_hash."""

    policies: tuple[EvidencePolicy, ...] = ()

    @model_validator(mode="after")
    def _unique_hashes(self) -> EvidencePolicyRegistry:
        seen: set[str] = set()
        for policy in self.policies:
            ch = policy.content_hash
            if ch in seen:
                raise ValueError(
                    f"duplicate content_hash in EvidencePolicyRegistry: {ch}"
                )
            seen.add(ch)
        return self

    def resolve(self, ref: str) -> EvidencePolicy | None:
        for policy in self.policies:
            if policy.content_hash == ref:
                return policy
        return None
