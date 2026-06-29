"""VerificationPolicy, ExecutionContract, EvidenceProvenance, EvidenceLicensingInfo.

V2.0 evidence-licensed capability grammar (pure / numpy-free).
"""
from __future__ import annotations

import math
import re
from typing import Literal

from pydantic import model_validator

from .base import _Model
from .licensing import LicenseRoute, MaterializationContext

# ---------------------------------------------------------------------------
# Shared regex helpers (mirror evidence_policy.py)
# ---------------------------------------------------------------------------

_SHA256_REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_BENCH_REF_RE = re.compile(r"^bench:sha256:[0-9a-f]{64}$")


def _check_sha256(field: str, value: str) -> None:
    if not _SHA256_REF_RE.match(value):
        raise ValueError(
            f"{field} must be 'sha256:<64 lowercase hex>', got {value!r}"
        )


# ---------------------------------------------------------------------------
# VerificationPolicy
# ---------------------------------------------------------------------------


class VerificationPolicy(_Model):
    """Governs how a capability's evidence is produced and verified.

    Two complete modes are recognised:

    * ``recompute_pair`` — criterion-based, implementation-independent pair of
      runs; no external evidence policy; exactly 2 adapters.
    * ``single``         — e-value discovery against a baseline ground truth;
      refers to an external EvidencePolicy; exactly 1 adapter.
    """

    execution: Literal["recompute_pair", "single"]
    result_rule: Literal["criterion", "evalue_discovery"]
    independence_requirement: Literal["implementation", "baseline_ground_truth"]
    evidence_policy_ref: str | None = None
    min_adapters: int

    @model_validator(mode="after")
    def _validate_mode(self) -> VerificationPolicy:
        if self.execution == "recompute_pair":
            errors: list[str] = []
            if self.result_rule != "criterion":
                errors.append("result_rule must be 'criterion' for recompute_pair mode")
            if self.independence_requirement != "implementation":
                errors.append(
                    "independence_requirement must be 'implementation' for recompute_pair mode"
                )
            if self.evidence_policy_ref is not None:
                errors.append("evidence_policy_ref must be None for recompute_pair mode")
            if self.min_adapters != 2:
                errors.append("min_adapters must be 2 for recompute_pair mode")
            if errors:
                raise ValueError("; ".join(errors))
        else:  # single
            errors = []
            if self.result_rule != "evalue_discovery":
                errors.append("result_rule must be 'evalue_discovery' for single mode")
            if self.independence_requirement != "baseline_ground_truth":
                errors.append(
                    "independence_requirement must be 'baseline_ground_truth' for single mode"
                )
            if self.evidence_policy_ref is None:
                errors.append("evidence_policy_ref is required for single mode")
            elif not _SHA256_REF_RE.match(self.evidence_policy_ref):
                errors.append(
                    f"evidence_policy_ref must be sha256-shaped, got {self.evidence_policy_ref!r}"
                )
            if self.min_adapters != 1:
                errors.append("min_adapters must be 1 for single mode")
            if errors:
                raise ValueError("; ".join(errors))
        return self


# ---------------------------------------------------------------------------
# ExecutionContract
# ---------------------------------------------------------------------------


class ExecutionContract(_Model):
    """Binds a capability version to a specific evidence policy and descriptor."""

    capability_id: str
    capability_version: str
    evidence_policy_ref: str
    capability_descriptor_ref: str

    @model_validator(mode="after")
    def _validate(self) -> ExecutionContract:
        if not self.capability_id.strip():
            raise ValueError("capability_id must be non-empty")
        if not self.capability_version.strip():
            raise ValueError("capability_version must be non-empty")
        _check_sha256("evidence_policy_ref", self.evidence_policy_ref)
        _check_sha256("capability_descriptor_ref", self.capability_descriptor_ref)
        return self


# ---------------------------------------------------------------------------
# EvidenceProvenance
# ---------------------------------------------------------------------------


class EvidenceProvenance(_Model):
    """Immutable record of how a single e-value was produced."""

    claim_id: str
    executor_descriptor_ref: str
    evidence_policy_ref: str
    benchmark_ref: str          # bench:sha256:<hex>
    baseline_config_ref: str
    baseline_predictions_ref: str
    predictor_config_ref: str
    capability_descriptor_ref: str
    oracle_dossier_ref: str | None = None
    observed_advantage: float
    theta0: float
    e_value: float
    execution_contract_digest: str
    fdr_test_index: int
    alpha_allocated: float

    @model_validator(mode="after")
    def _validate(self) -> EvidenceProvenance:
        # claim_id non-empty
        if not self.claim_id.strip():
            raise ValueError("claim_id must be non-empty")

        # sha256-shaped refs
        for name, val in [
            ("executor_descriptor_ref", self.executor_descriptor_ref),
            ("evidence_policy_ref", self.evidence_policy_ref),
            ("baseline_config_ref", self.baseline_config_ref),
            ("baseline_predictions_ref", self.baseline_predictions_ref),
            ("predictor_config_ref", self.predictor_config_ref),
            ("capability_descriptor_ref", self.capability_descriptor_ref),
            ("execution_contract_digest", self.execution_contract_digest),
        ]:
            _check_sha256(name, val)

        # oracle_dossier_ref optional but must be sha256-shaped when present
        if self.oracle_dossier_ref is not None:
            _check_sha256("oracle_dossier_ref", self.oracle_dossier_ref)

        # benchmark_ref: bench:sha256:<hex>
        if not _BENCH_REF_RE.match(self.benchmark_ref):
            raise ValueError(
                f"benchmark_ref must be 'bench:sha256:<64 hex>', got {self.benchmark_ref!r}"
            )

        # observed_advantage ∈ [−1, 1]
        if not (-1.0 <= self.observed_advantage <= 1.0):
            raise ValueError(
                f"observed_advantage must be in [-1, 1], got {self.observed_advantage}"
            )

        # theta0: finite and 0 <= theta0 < 1
        if not math.isfinite(self.theta0):
            raise ValueError(f"theta0 must be finite, got {self.theta0}")
        if not (0.0 <= self.theta0 < 1.0):
            raise ValueError(f"theta0 must satisfy 0 <= theta0 < 1, got {self.theta0}")

        # e_value: not NaN, >= 0 (+inf permitted)
        if math.isnan(self.e_value):
            raise ValueError("e_value must not be NaN")
        if self.e_value < 0.0:
            raise ValueError(f"e_value must be >= 0, got {self.e_value}")

        # fdr_test_index > 0
        if self.fdr_test_index <= 0:
            raise ValueError(f"fdr_test_index must be > 0, got {self.fdr_test_index}")

        # 0 < alpha_allocated <= 1
        if not (0.0 < self.alpha_allocated <= 1.0):
            raise ValueError(
                f"alpha_allocated must satisfy 0 < alpha_allocated <= 1, "
                f"got {self.alpha_allocated}"
            )

        return self


# ---------------------------------------------------------------------------
# EvidenceLicensingInfo
# ---------------------------------------------------------------------------


class EvidenceLicensingInfo(_Model):
    """Licensing info for a claim backed by the evidence-licensed pathway."""

    route: LicenseRoute
    verification_standing: Literal["single_source_baseline"]
    evidence_provenance: EvidenceProvenance
    materialization: MaterializationContext
