"""L3 — the value-based defeat graph over claims (spec §3.5).

A corpus-level module of pure functions over edges, mirroring equivalence.py — no
fields are added to Claim. Edges are attacks (undermine/undercut/rebut/reclassify/
reinterpret) or support (evidence_for). Which attacks actually DEFEAT is filtered by
the Phase-4 Pareto strength order (effective_defeats); the grounded extension over
those effective defeats says which claims are IN. Imports nothing from
polymer_formalclaim (isolation guard).
"""
from __future__ import annotations

from enum import Enum

from pydantic import model_validator

from .base import _Model


class DefeatEdgeKind(str, Enum):
    UNDERMINE = "undermine"      # attacks a premise / the data basis
    UNDERCUT = "undercut"        # attacks the inferential warrant
    REBUT = "rebut"              # asserts the contrary conclusion
    RECLASSIFY = "reclassify"    # disputes the pattern/profile applied
    REINTERPRET = "reinterpret"  # meaning moved, statistics unchanged
    EVIDENCE_FOR = "evidence_for"  # support, never a defeat


ATTACK_KINDS = frozenset(
    {
        DefeatEdgeKind.UNDERMINE,
        DefeatEdgeKind.UNDERCUT,
        DefeatEdgeKind.REBUT,
        DefeatEdgeKind.RECLASSIFY,
        DefeatEdgeKind.REINTERPRET,
    }
)


class DefeatEdge(_Model):
    source: str
    target: str
    kind: DefeatEdgeKind
    note: str | None = None

    @model_validator(mode="after")
    def _no_self_loop(self) -> "DefeatEdge":
        if self.source == self.target:
            raise ValueError(
                "a DefeatEdge must relate two DISTINCT claims (no self-defeat/self-support)"
            )
        return self
