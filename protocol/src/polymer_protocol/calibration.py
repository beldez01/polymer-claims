"""Warrant-tiered calibration ledger (pure, numpy-free, deterministic).

Calibration is an INSTRUMENT, not a gate: it measures the gate's reliability and never changes a
claim's status. This module holds the data model, the pure aggregation (`calibration_summary`), and
the pure ANCHORED transition function (`anchored_resolutions`). All impurity — synthetic data, the
e-value computation, persistence, epoch allocation, rendering — lives umbrella-side.
"""
from __future__ import annotations

from enum import Enum

from pydantic import model_validator

from .base import _Model


class ResolutionKind(str, Enum):
    DEFINITIONAL = "definitional"
    ANCHORED = "anchored"
    ATTESTED = "attested"


class CalibrationTarget(str, Enum):
    REALIZED_FDR = "realized_fdr"
    WARRANT_SURVIVAL = "warrant_survival"
    EXTERNAL_DISAGREEMENT = "external_disagreement"


class ResolutionVerdict(str, Enum):
    UPHELD = "upheld"
    FAILED = "failed"
    UNRESOLVED = "unresolved"
    SUPERSEDED = "superseded"


class PressureKind(str, Enum):
    DEFEAT = "defeat"
    DRIFT = "drift"
    RED_TEAM = "red_team"


# the one legal (kind -> target) coupling
_TARGET_FOR_KIND = {
    ResolutionKind.DEFINITIONAL: CalibrationTarget.REALIZED_FDR,
    ResolutionKind.ANCHORED: CalibrationTarget.WARRANT_SURVIVAL,
    ResolutionKind.ATTESTED: CalibrationTarget.EXTERNAL_DISAGREEMENT,
}


class ResolutionRecord(_Model):
    """One resolved license, keyed to a (subject_claim_id, license_epoch). Created ONLY for claims
    the gate LICENSED — calibration is about the reliability of earned standing."""

    subject_claim_id: str
    license_epoch: int
    resolution_kind: ResolutionKind
    calibration_target: CalibrationTarget
    verdict: ResolutionVerdict
    stated_q: float
    observed_at_cycle: int
    # present-only-when-kind (additive/optional):
    constructed_truth: bool | None = None   # definitional — known ground truth
    model_id: str | None = None             # definitional — which GeneratingModelParams
    batch_id: str | None = None             # definitional — which synthetic batch (per-batch FDP)
    pressure_kind: PressureKind | None = None   # anchored — the survived/failed pressure event
    attestation_ref: str | None = None      # attested — external reference
    source_claim_id: str | None = None      # attested — set iff the event is itself a corpus claim

    @property
    def feeds_headline_q(self) -> bool:
        return (
            self.resolution_kind == ResolutionKind.DEFINITIONAL
            and self.calibration_target == CalibrationTarget.REALIZED_FDR
        )

    @model_validator(mode="after")
    def _validate(self) -> "ResolutionRecord":
        k = self.resolution_kind
        if self.calibration_target != _TARGET_FOR_KIND[k]:
            raise ValueError(
                f"calibration_target {self.calibration_target.value} is not the target for "
                f"kind {k.value} (expected {_TARGET_FOR_KIND[k].value})"
            )
        defn = k == ResolutionKind.DEFINITIONAL
        anch = k == ResolutionKind.ANCHORED
        att = k == ResolutionKind.ATTESTED
        # present-only-when-kind
        if (self.constructed_truth is not None) != defn:
            raise ValueError("constructed_truth is present iff resolution_kind=definitional")
        if (self.model_id is not None) != defn:
            raise ValueError("model_id is present iff resolution_kind=definitional")
        if (self.pressure_kind is not None) != anch:
            raise ValueError("pressure_kind is present iff resolution_kind=anchored")
        if self.attestation_ref is not None and not att:
            raise ValueError("attestation_ref is valid only when resolution_kind=attested")
        if self.source_claim_id is not None and not att:
            raise ValueError("source_claim_id is valid only when resolution_kind=attested")
        # definitional needs a batch_id (the per-batch FDP fold depends on it)
        if defn and self.batch_id is None:
            raise ValueError("definitional records require a batch_id")
        if not defn and self.batch_id is not None:
            raise ValueError("batch_id is valid only when resolution_kind=definitional")
        # a DEFINITIONAL record always has known truth -> never unresolved
        if defn and self.verdict == ResolutionVerdict.UNRESOLVED:
            raise ValueError("definitional records cannot be unresolved (truth is known)")
        return self
