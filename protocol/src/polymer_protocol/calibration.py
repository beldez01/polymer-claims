"""Warrant-tiered calibration ledger (pure, numpy-free, deterministic).

Calibration is an INSTRUMENT, not a gate: it measures the gate's reliability and never changes a
claim's status. This module holds the data model, the pure aggregation (`calibration_summary`), and
the pure ANCHORED transition function (`anchored_resolutions`). All impurity — synthetic data, the
e-value computation, persistence, epoch allocation, rendering — lives umbrella-side.
"""
from __future__ import annotations

import math
from collections import defaultdict
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


class GeneratingModelParams(_Model):
    """The disclosed assumption behind one DEFINITIONAL batch (named on the certificate)."""
    model_id: str
    n_per_group: int
    n_probes_per_region: int
    effect_size: float
    dispersion: float
    fraction_true: float
    tau: float
    target_fdr: float
    n_generated: int
    seed_set: tuple[int, ...]


class CalibrationLedger(_Model):
    records: tuple[ResolutionRecord, ...] = ()
    generating_models: tuple[GeneratingModelParams, ...] = ()
    default_target_q: float | None = None   # optional CLI/report default hint only — NOT authoritative


class TierStat(_Model):
    n_total: int            # tier denominator population (per-tier meaning; see calibration_summary)
    n_failed: int
    n_unresolved: int = 0   # anchored/attested only
    n_superseded: int = 0   # anchored only — terminal, excluded from the failure denominator
    realized_rate: float | None = None
    pooled_rate: float | None = None     # DEFINITIONAL secondary: Σfailed/Σlicensed
    ci_low: float | None = None
    ci_high: float | None = None
    ci_method: str | None = None         # "normal_0.95" (definitional) | "wilson_0.95" (anchored)
    n_batches: int | None = None         # DEFINITIONAL
    n_generated: int | None = None       # DEFINITIONAL


class CalibrationReport(_Model):
    target_q: float
    observation_span_cycles: int | None = None
    definitional: TierStat
    anchored: TierStat
    attested: TierStat


_Z = 1.959963984540054  # 95% normal quantile


def _wilson_ci(k: int, n: int) -> tuple[float, float] | tuple[None, None]:
    if n == 0:
        return (None, None)
    p = k / n
    z2 = _Z * _Z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (_Z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _normal_ci(values: list[float]) -> tuple[float, float] | tuple[None, None]:
    n = len(values)
    if n == 0:
        return (None, None)
    mean = sum(values) / n
    if n == 1:
        return (mean, mean)
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    half = _Z * math.sqrt(var / n)
    return (max(0.0, mean - half), min(1.0, mean + half))


def _definitional_stat(records, target_q, models) -> TierStat:
    # n_generated comes from the generating models for THIS target_q (records only capture LICENSED
    # claims; the withheld ones live only in the model's n_generated count).
    n_generated = sum(m.n_generated for m in models if m.target_fdr == target_q)
    recs = [r for r in records
            if r.resolution_kind == ResolutionKind.DEFINITIONAL and r.stated_q == target_q]
    n_total = len(recs)
    n_failed = sum(1 for r in recs if r.verdict == ResolutionVerdict.FAILED)
    if n_total == 0:
        return TierStat(n_total=0, n_failed=0, realized_rate=None, n_batches=0,
                        n_generated=n_generated)
    by_batch: dict[str, list[bool]] = defaultdict(list)
    for r in recs:
        by_batch[r.batch_id].append(r.verdict == ResolutionVerdict.FAILED)
    fdps = [sum(b) / len(b) for b in by_batch.values()]  # licensed_b == len(b) > 0 here
    realized = sum(fdps) / len(fdps)
    lo, hi = _normal_ci(fdps)
    return TierStat(
        n_total=n_total, n_failed=n_failed,
        realized_rate=realized, pooled_rate=n_failed / n_total,
        ci_low=lo, ci_high=hi, ci_method="normal_0.95",
        n_batches=len(by_batch),
        n_generated=n_generated or None,
    )


def _anchored_stat(records: tuple[ResolutionRecord, ...]) -> TierStat:
    recs = [r for r in records if r.resolution_kind == ResolutionKind.ANCHORED]
    n_failed = sum(1 for r in recs if r.verdict == ResolutionVerdict.FAILED)
    n_upheld = sum(1 for r in recs if r.verdict == ResolutionVerdict.UPHELD)
    n_unresolved = sum(1 for r in recs if r.verdict == ResolutionVerdict.UNRESOLVED)
    n_superseded = sum(1 for r in recs if r.verdict == ResolutionVerdict.SUPERSEDED)
    denom = n_failed + n_upheld
    lo, hi = _wilson_ci(n_failed, denom)
    return TierStat(
        n_total=denom, n_failed=n_failed, n_unresolved=n_unresolved, n_superseded=n_superseded,
        realized_rate=(n_failed / denom if denom else None),
        ci_low=lo, ci_high=hi, ci_method=("wilson_0.95" if denom else None),
    )


def _attested_stat(records: tuple[ResolutionRecord, ...]) -> TierStat:
    recs = [r for r in records if r.resolution_kind == ResolutionKind.ATTESTED]
    n_failed = sum(1 for r in recs if r.verdict == ResolutionVerdict.FAILED)
    denom = sum(1 for r in recs if r.verdict in (ResolutionVerdict.FAILED, ResolutionVerdict.UPHELD))
    return TierStat(n_total=denom, n_failed=n_failed,
                    realized_rate=(n_failed / denom if denom else None))


def calibration_summary(ledger: CalibrationLedger, *, target_q: float) -> CalibrationReport:
    """Pure. A report summarizes ONE target_q (FDPs are not averaged across e-LOND targets)."""
    recs = ledger.records
    cycles = [r.observed_at_cycle for r in recs if r.resolution_kind == ResolutionKind.ANCHORED]
    span = (max(cycles) - min(cycles)) if cycles else None
    return CalibrationReport(
        target_q=target_q,
        observation_span_cycles=span,
        definitional=_definitional_stat(recs, target_q, ledger.generating_models),
        anchored=_anchored_stat(recs),
        attested=_attested_stat(recs),
    )
