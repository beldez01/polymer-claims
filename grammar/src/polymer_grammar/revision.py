"""L4 — AGM/TMS belief revision over the claim corpus (spec §3.5).

Belief-BASE AGM (Hansson): the consequence operation is the L1 inferential-neighborhood
closure (`entails` edges), inconsistency is `incompatible_with`. Entrenchment is a PARTIAL
order from StrengthVector (severity, evidence_against_null) + Status. Consistency
restoration incises the least-entrenched member of each conflict, surfacing robust vs
underdetermined retractions (mirroring blame.py). After any edit, the monotone status
recompute reuses defeat.grounded_extension. Imports nothing from polymer_formalclaim.
"""
from __future__ import annotations

from enum import Enum

from .claim import Claim
from .status import Status


class Entrench(str, Enum):
    GREATER = "greater"
    LESS = "less"
    EQUAL = "equal"
    INCOMPARABLE = "incomparable"


_STATUS_TIER = {
    Status.REJECTED: 0,
    Status.CONJECTURED: 1,
    Status.EXPLORATORY: 2,
    Status.PENDING: 3,
    Status.LICENSED: 4,
}

_ENTRENCH_AXES = ("severity", "evidence_against_null")


def compare_entrenchment(a: Claim, b: Claim) -> Entrench:
    """Partial entrenchment order (a relative to b). More entrenched = given up last.

    Coarse total tier on Status, then a PARTIAL sub-order on the strength axes
    (severity, evidence_against_null); INCOMPARABLE is a first-class outcome.
    """
    ta, tb = _STATUS_TIER[a.status], _STATUS_TIER[b.status]
    if ta != tb:
        return Entrench.GREATER if ta > tb else Entrench.LESS
    sa, sb = a.strength, b.strength
    if sa is None and sb is None:
        return Entrench.EQUAL
    if sa is None:
        return Entrench.LESS
    if sb is None:
        return Entrench.GREATER
    ge = all(getattr(sa, ax) >= getattr(sb, ax) for ax in _ENTRENCH_AXES)
    le = all(getattr(sa, ax) <= getattr(sb, ax) for ax in _ENTRENCH_AXES)
    if ge and le:
        return Entrench.EQUAL
    if ge:
        return Entrench.GREATER
    if le:
        return Entrench.LESS
    return Entrench.INCOMPARABLE
