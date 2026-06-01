"""Strength as a 6-axis Pareto partial order (spec §3.5).

AND = componentwise meet (weakest link); OR = componentwise join. Two claims with a
cross-axis trade-off are genuinely *incomparable* — there is no hidden scalar and no
Arrow-style aggregation. A claim is LICENSED only if it dominates a declared threshold
vector on EVERY axis.
"""
from __future__ import annotations

from pydantic import Field

from .base import _Model

AXES: tuple[str, ...] = (
    "magnitude",
    "uncertainty",
    "evidence_against_null",
    "severity",
    "world_contact",
    "explanatory_virtue",
)


class StrengthVector(_Model):
    magnitude: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    evidence_against_null: float = Field(ge=0.0, le=1.0)
    severity: float = Field(ge=0.0, le=1.0)
    world_contact: float = Field(ge=0.0, le=1.0)
    explanatory_virtue: float = Field(ge=0.0, le=1.0)

    def meet(self, other: "StrengthVector") -> "StrengthVector":
        return StrengthVector(**{ax: min(getattr(self, ax), getattr(other, ax)) for ax in AXES})

    def join(self, other: "StrengthVector") -> "StrengthVector":
        return StrengthVector(**{ax: max(getattr(self, ax), getattr(other, ax)) for ax in AXES})

    def dominates(self, other: "StrengthVector") -> bool:
        return all(getattr(self, ax) >= getattr(other, ax) for ax in AXES)

    def comparable(self, other: "StrengthVector") -> bool:
        return self.dominates(other) or other.dominates(self)


def licensed(candidate: StrengthVector, threshold: StrengthVector) -> bool:
    """LICENSED <=> candidate dominates the threshold on every axis (conjunctive gate)."""
    return candidate.dominates(threshold)
