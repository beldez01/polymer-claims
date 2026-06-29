"""Governance — data hazard + access scope of a claim (spec §5 #3).

Claim-level (v1.3 has no per-data-dependency model). Feeds the protocol's SAFETY-GATE
(via requires_safety_review) and the dormant `unreproducible_by_governance` status (via
blocks_reproduction). Load-bearing for the controlled-access genomic surface. The grammar
represents the posture; the protocol acts. Imports nothing from polymer_protocol/polymer_claims.
"""
from __future__ import annotations

from enum import Enum

from .base import _Model


class HazardClass(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    DUAL_USE = "dual_use"


class AccessScope(str, Enum):
    PUBLIC = "public"
    REGISTERED_ACCESS = "registered_access"
    CONTROLLED = "controlled"
    RESTRICTED = "restricted"
    EMBARGOED = "embargoed"


class Governance(_Model):
    hazard_class: HazardClass = HazardClass.NONE
    access_scope: AccessScope = AccessScope.PUBLIC
    note: str | None = None


def blocks_reproduction(governance: Governance) -> bool:
    """True iff the access scope prevents independent reproduction (restricted/embargoed) —
    the protocol uses this to set the `unreproducible_by_governance` PENDING reason."""
    return governance.access_scope in {AccessScope.RESTRICTED, AccessScope.EMBARGOED}


def requires_safety_review(governance: Governance) -> bool:
    """True iff the hazard class warrants the protocol's SAFETY-GATE (high/dual_use)."""
    return governance.hazard_class in {HazardClass.HIGH, HazardClass.DUAL_USE}
