"""Morphospace trichotomy (neg-whisper ⑤) — separate FORBIDDEN from UNOBSERVED.

The classic morphospace weakness (measurement-foundation §7.8): an *empty* region (nobody looked)
is indistinguishable from a *forbidden* one (a genuine constraint, severely tested). This module
gives the operational separation the doc asks for — no more, no less (forbidden-vs-unobserved is
undecidable in general; this is the severity-backed operational split).

FIREWALL (licensing-not-meaning): a FORBIDDEN state is a LICENSED NEGATIVE — earned warrant for
ABSENCE at a stated severity — NOT metaphysical impossibility. It is a licensing STATUS, not a
meaning verdict. This module reads status; it never changes it, and the licensing gate is untouched
(a negative claim licenses through the same air-gap + e-value machinery as any other, via a
bound-below-threshold criterion).

Pure, stdlib only; reads grammar IR; adds no Corpus collection.
"""
from __future__ import annotations

from enum import Enum

from .claim import Claim
from .pattern import get_pattern
from .status import PendingReason, Status

FIREWALL_STATEMENT = (
    "A FORBIDDEN morphospace state is a LICENSED NEGATIVE: earned warrant for ABSENCE at a stated "
    "severity — NOT metaphysical impossibility. It is a licensing status, not a meaning verdict "
    "(the licensing-not-meaning firewall). Forbidden-vs-unobserved is separated operationally by "
    "severity; it is not resolved in general (undecidable in the limit)."
)


class MorphospaceState(str, Enum):
    OCCUPIED = "occupied"        # a LICENSED presence claim — the region contains an effect
    FORBIDDEN = "forbidden"      # a LICENSED severity-backed NEGATIVE — warranted absence at severity
    UNOBSERVED = "unobserved"    # PENDING untested — nobody has looked yet
    OTHER = "other"              # REJECTED / conjectured / other-pending / sub-severity licensed negative


def morphospace_state(
    claim: Claim, *, asserts_absence: bool, severity_floor: float = 0.0
) -> MorphospaceState:
    """Classify a claim's morphospace cell. ``asserts_absence`` = whether the claim's pattern is a
    licensed-negative pattern (resolve it from the registry, or use ``morphospace_state_of``).
    A licensed negative counts as FORBIDDEN only when its ``strength.severity`` clears
    ``severity_floor`` — "forbidden = a licensed negative with high severity"; a weaker one is OTHER.
    """
    if claim.status == Status.LICENSED:
        if not asserts_absence:
            return MorphospaceState.OCCUPIED
        severity = claim.strength.severity if claim.strength is not None else 0.0
        return MorphospaceState.FORBIDDEN if severity >= severity_floor else MorphospaceState.OTHER
    if claim.status == Status.PENDING and claim.pending_reason == PendingReason.UNTESTED:
        return MorphospaceState.UNOBSERVED
    return MorphospaceState.OTHER


def morphospace_state_of(claim: Claim, *, severity_floor: float = 0.0) -> MorphospaceState:
    """``morphospace_state`` with ``asserts_absence`` resolved from the claim's registered pattern."""
    try:
        asserts_absence = get_pattern(claim.pattern.id, claim.pattern.version).asserts_absence
    except KeyError:
        asserts_absence = False  # unregistered pattern -> treat as a presence pattern
    return morphospace_state(claim, asserts_absence=asserts_absence, severity_floor=severity_floor)
