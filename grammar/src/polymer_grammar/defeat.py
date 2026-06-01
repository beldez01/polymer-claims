"""L3 — the value-based defeat graph over claims (spec §3.5).

A corpus-level module of pure functions over edges, mirroring equivalence.py — no
fields are added to Claim. Edges are attacks (undermine/undercut/rebut/reclassify/
reinterpret) or support (evidence_for). Which attacks actually DEFEAT is filtered by
the Phase-4 Pareto strength order (effective_defeats); the grounded extension over
those effective defeats says which claims are IN. Imports nothing from
polymer_formalclaim (isolation guard).
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum

from pydantic import model_validator

from .base import _Model
from .strength import StrengthVector


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


def effective_defeats(
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
) -> frozenset[tuple[str, str]]:
    """(source, target) attack pairs that survive the VAF value filter.

    An attack defeats UNLESS the target strength-dominates the source (Pareto). When
    either strength is absent or the two are incomparable, the attack stands — absence
    of proven superiority is not superiority. `evidence_for` is never a defeat.
    """
    out: set[tuple[str, str]] = set()
    for e in edges:
        if e.kind not in ATTACK_KINDS:
            continue
        s_src = strength.get(e.source)
        s_tgt = strength.get(e.target)
        if s_src is not None and s_tgt is not None and s_tgt.dominates(s_src):
            continue  # target at-least-as-strong on every axis (>=, standard VAF preference) -> attack filtered out
        out.add((e.source, e.target))
    return frozenset(out)
