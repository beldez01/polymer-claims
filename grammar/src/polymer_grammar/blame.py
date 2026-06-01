"""L3 — Duhem–Quine blame-sets (spec §3.5).

When a contradiction arises, blame can fall on any member of a claim/auxiliary bundle
(Duhem). The protocol SUPPLIES the candidate minimal blame-assignments (computing them
is NP-hard and would break PTIME); the grammar only does the tractable set algebra:
intersection = robustly blamed, union = possibly blamed, difference = underdetermined
(-> PENDING duhem_underdetermined). Targets may name claims OR auxiliary assumptions.
"""
from __future__ import annotations

from pydantic import model_validator

from .base import _Model
from .status import PendingReason, Status


class BlameAssignment(_Model):
    targets: tuple[str, ...]  # claim ids OR auxiliary-assumption ids
    note: str | None = None

    @model_validator(mode="after")
    def _nonempty(self) -> "BlameAssignment":
        if not self.targets:
            raise ValueError("a BlameAssignment must name >=1 target")
        return self


class BlameSet(_Model):
    contradiction_id: str
    assignments: tuple[BlameAssignment, ...]

    @model_validator(mode="after")
    def _has_assignment(self) -> "BlameSet":
        if not self.assignments:
            raise ValueError("a BlameSet must carry >=1 minimal blame-assignment")
        return self


class BlameVerdict(_Model):
    robustly_blamed: frozenset[str]   # in EVERY assignment -> robustly defeated / OUT
    possibly_blamed: frozenset[str]   # the union
    underdetermined: frozenset[str]   # union - intersection -> PENDING duhem_underdetermined


def aggregate_blame(blame: BlameSet) -> BlameVerdict:
    """intersection -> robustly_blamed; union -> possibly_blamed; difference -> underdetermined."""
    sets = [frozenset(a.targets) for a in blame.assignments]
    union = frozenset().union(*sets)
    intersection = sets[0]
    for s in sets[1:]:
        intersection = intersection & s
    return BlameVerdict(
        robustly_blamed=intersection,
        possibly_blamed=union,
        underdetermined=union - intersection,
    )


def duhem_status(
    claim_id: str, verdict: BlameVerdict
) -> tuple[Status, PendingReason | None] | None:
    """The (status, reason) the corpus fold should set for `claim_id`, or None if the
    claim is not implicated. Underdetermined -> PENDING duhem; robustly blamed -> REJECTED."""
    # from aggregate_blame these sets are disjoint; checking underdetermined first is conservative for hand-built verdicts
    if claim_id in verdict.underdetermined:
        return (Status.PENDING, PendingReason.DUHEM_UNDERDETERMINED)
    if claim_id in verdict.robustly_blamed:
        return (Status.REJECTED, None)
    return None
