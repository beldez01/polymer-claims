"""oracle.py — the oracle credibility dossier (unified spec §5 #2 / daemon D2).

Represents how an oracle (API endpoint / R routine / assay) was validated, and caps the
EMPIRICAL strength axes of any claim it grounds by the oracle's validation tier. The grammar
ships the IR + the pure capping math; the protocol decides policy (resolution + the
LICENSED-seam cap). The tier is about the APPARATUS, never the claim's literature precedent.
Imports nothing from polymer_formalclaim.
"""
from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from pydantic import Field

from .base import _Model
from .operations import EvaluationPlan
from .subject import Subject
from .strength import AXES, StrengthVector


class ValidationTier(str, Enum):
    UNVALIDATED = "unvalidated"      # no dossier / unresolved / out-of-domain
    INDIRECT = "indirect"            # checked against literature-reported / heuristic values
    BENCHMARKED = "benchmarked"      # against a computational ground-truth set
    ANCHORED = "anchored"            # against a direct wet-lab/clinical anchor, bounded domain
    GOLD = "gold"                    # gold-standard, broadly validated


# str-Enum (JSON-faithful) -> explicit rank for ordering, mirroring revision._STATUS_TIER.
_TIER_RANK = {
    ValidationTier.UNVALIDATED: 0,
    ValidationTier.INDIRECT: 1,
    ValidationTier.BENCHMARKED: 2,
    ValidationTier.ANCHORED: 3,
    ValidationTier.GOLD: 4,
}

# Goodness empirical axes the tier ceiling caps DOWN (higher = stronger). `uncertainty` is ALSO
# apparatus-bounded but REVERSE-polarity (higher = weaker), so it is floored UP in cap_strength, not
# capped here. severity + explanatory_virtue are theory axes (set by argument) -> never touched.
_GOODNESS_EMPIRICAL_AXES = ("magnitude", "evidence_against_null", "world_contact")

# v1 empirical-axis ceiling per tier (monotone; endpoints pinned at 0.0/1.0).
# v1 ladder — tunable; calibrate against empirical oracle-validation sets later.
_TIER_CEILING = {
    ValidationTier.UNVALIDATED: 0.0,
    ValidationTier.INDIRECT: 0.4,
    ValidationTier.BENCHMARKED: 0.6,
    ValidationTier.ANCHORED: 0.85,
    ValidationTier.GOLD: 1.0,
}


def weakest_tier(tiers: Iterable[ValidationTier]) -> ValidationTier:
    """The lowest-rank tier (a chain is only as strong as its weakest oracle). Empty -> GOLD,
    the no-constraint identity (GOLD's ceiling is all-1.0, so capping by it is a no-op).
    Callers that require >=1 oracle must guard the empty case themselves (oracle_cap checks
    refs before calling)."""
    ts = list(tiers)
    if not ts:
        return ValidationTier.GOLD
    return min(ts, key=lambda t: _TIER_RANK[t])


def tier_ceiling(tier: ValidationTier) -> StrengthVector:
    """Per-axis ceiling for the GOODNESS empirical axes (capped down to c). `uncertainty` and the theory
    axes stay 1.0 here — uncertainty is reverse-polarity and is floored UP in cap_strength instead."""
    c = _TIER_CEILING[tier]
    return StrengthVector(**{ax: (c if ax in _GOODNESS_EMPIRICAL_AXES else 1.0) for ax in AXES})


def cap_strength(
    strength: StrengthVector | None, tier: ValidationTier
) -> StrengthVector | None:
    """`strength` capped by the tier. Goodness empirical axes meet the ceiling (componentwise min);
    the reverse-polarity `uncertainty` axis is floored UP to (1 - ceiling) — a weak apparatus makes a
    claim MORE uncertain, not less (F2). Theory axes (severity, explanatory_virtue) uncapped. None -> None."""
    if strength is None:
        return None
    c = _TIER_CEILING[tier]
    capped = strength.meet(tier_ceiling(tier))  # caps the 3 goodness axes; uncertainty/theory are no-ops
    return capped.model_copy(update={"uncertainty": max(strength.uncertainty, 1.0 - c)})


class ApplicabilityDomain(_Model):
    """The bounded domain an oracle is qualified for. `subject_kinds` lists the Subject
    discriminator kinds it covers (empty = unbounded); `predicates` are prose qualifications
    for human audit (not machine-checked in the spine)."""

    # v1: subject_kinds are free strings, not validated against the Subject discriminator set
    # — a typo silently never matches (conservative out-of-domain).
    subject_kinds: tuple[str, ...] = ()
    predicates: tuple[str, ...] = ()


class OracleDossier(_Model):
    """An oracle's credibility-qualification record. `oracle_id` matches an
    `OperationNode.oracle_ref`. `relative_uncertainty` is representable now; its propagation
    into executed leaves is deferred (spec §8)."""

    oracle_id: str = Field(min_length=1)
    validation_tier: ValidationTier
    applicability_domain: ApplicabilityDomain = Field(default_factory=ApplicabilityDomain)
    anchor: str | None = None
    relative_uncertainty: float | None = Field(default=None, ge=0.0)


def in_domain(domain: ApplicabilityDomain, subject: Subject | None) -> bool:
    """Is `subject` within the oracle's qualified domain? Unbounded domain (no subject_kinds)
    -> always True. A bounded domain qualifies only its listed Subject kinds; a claim with no
    subject can't be confirmed in a bounded domain -> False (conservative)."""
    if not domain.subject_kinds:
        return True
    if subject is None:
        return False
    return subject.kind in domain.subject_kinds


def referenced_oracle_ids(plan: EvaluationPlan) -> frozenset[str]:
    """The set of oracle_refs the plan's operation nodes name (None refs excluded)."""
    return frozenset(n.oracle_ref for n in plan.graph.nodes if n.oracle_ref is not None)
