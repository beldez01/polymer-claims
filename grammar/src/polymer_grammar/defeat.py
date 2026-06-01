"""L3 — the value-based defeat graph over claims (spec §3.5).

A corpus-level module of pure functions over edges, mirroring equivalence.py — no
fields are added to Claim. Edges are attacks (undermine/undercut/rebut/reclassify/
reinterpret) or support (evidence_for). Which attacks actually DEFEAT is filtered by
the Phase-4 Pareto strength order (effective_defeats); the grounded extension over
those effective defeats says which claims are IN. Imports nothing from
polymer_formalclaim (isolation guard).
"""
from __future__ import annotations

from collections import defaultdict
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


def _grounded_defeats(
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
) -> frozenset[tuple[str, str]]:
    """Defeat relation for grounded semantics: attack stands unless the target
    STRICTLY dominates the source (all axes strictly greater). Equal strength
    leaves the attack standing — neither side can claim preference — consistent
    with the Dung grounded extension semantics where tie = no preferred winner.

    This differs from ``effective_defeats`` (which uses ``>=`` per the VAF spec
    for unidirectional claim evaluation) only in the equality edge case.
    ``evidence_for`` is never a defeat here either.
    """
    out: set[tuple[str, str]] = set()
    for e in edges:
        if e.kind not in ATTACK_KINDS:
            continue
        s_src = strength.get(e.source)
        s_tgt = strength.get(e.target)
        # Filter only when target STRICTLY dominates source on every axis (all >).
        # Equal-strength attacks stand: no side proves superiority.
        if (
            s_src is not None
            and s_tgt is not None
            and all(
                getattr(s_tgt, ax) > getattr(s_src, ax)
                for ax in ("magnitude", "uncertainty", "evidence_against_null",
                           "severity", "world_contact", "explanatory_virtue")
            )
        ):
            continue
        out.add((e.source, e.target))
    return frozenset(out)


def grounded_extension(
    claim_ids: Iterable[str],
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
) -> frozenset[str]:
    """The IN set under grounded semantics over effective defeats (PTIME least fixpoint).

    F(S) = { a | every effective-attacker of a is itself effectively-attacked by some
    member of S }. Start from the empty set and add acceptable arguments until fixpoint;
    monotone F + add-only => the unique grounded extension. Edge endpoints not in
    claim_ids (e.g. synthetic refutation nodes) participate as nodes.

    Defeat here uses strict dominance (all axes strictly >) so that equal-strength
    mutual attacks are NOT filtered — neither side has proven preference, so the
    grounded extension leaves both OUT. See ``_grounded_defeats`` for rationale.
    """
    edges_list = list(edges)
    defeats = _grounded_defeats(edges_list, strength)
    nodes: set[str] = set(claim_ids)
    attackers: dict[str, set[str]] = defaultdict(set)
    for src, tgt in defeats:
        attackers[tgt].add(src)
        nodes.add(src)
        nodes.add(tgt)

    accepted: set[str] = set()
    changed = True
    while changed:
        changed = False
        for a in nodes:
            if a in accepted:
                continue
            if all(
                any((c, b) in defeats for c in accepted)
                for b in attackers.get(a, ())
            ):
                accepted.add(a)
                changed = True
    return frozenset(accepted)
