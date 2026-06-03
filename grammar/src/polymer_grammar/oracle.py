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

# Empirical (apparatus-bounded) axes the ceiling caps. severity + explanatory_virtue are
# test-design / theory axes (set by argument, not apparatus) -> never capped.
_EMPIRICAL_AXES = ("magnitude", "uncertainty", "evidence_against_null", "world_contact")

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
    """The per-axis strength ceiling a tier imposes: empirical axes carry the tier ceiling;
    theory axes (severity, explanatory_virtue) stay at 1.0 (uncapped)."""
    c = _TIER_CEILING[tier]
    return StrengthVector(**{ax: (c if ax in _EMPIRICAL_AXES else 1.0) for ax in AXES})


def cap_strength(
    strength: StrengthVector | None, tier: ValidationTier
) -> StrengthVector | None:
    """`strength` meet the tier ceiling (componentwise min) — caps only the empirical axes
    (theory-axis ceilings are 1.0). None in -> None out (nothing to cap)."""
    if strength is None:
        return None
    return strength.meet(tier_ceiling(tier))
