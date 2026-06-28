"""L3 — the value-based defeat graph over claims (spec §3.5).

A corpus-level module of pure functions over edges, mirroring equivalence.py — no
fields are added to Claim. Edges are attacks (undermine/undercut/rebut/reclassify/
reinterpret) or support (evidence_for). Which attacks actually DEFEAT is filtered by
the Phase-4 Pareto strength order (effective_defeats); the grounded extension over
those effective defeats says which claims are IN. Imports nothing from
polymer_protocol/polymer_claims (isolation guard).
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import model_validator

from .base import _Model
from .licensing import Satisfaction, SatisfactionVerdict
from .proposition import NeighborEdgeKind
from .status import Status
from .strength import StrengthVector

if TYPE_CHECKING:
    from .claim import Claim


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

# Only defeats that ENTAIL the effect-null (H0: effect <= tau) may refund the e-LOND ledger
# (evalue-claim-graph/refund-validity.md Theorem 1). Edge kind is a coarse proxy: REBUT asserts
# the contrary conclusion -> entails the null. UNDERMINE attacks the data basis but does NOT by
# itself establish the null (the effect may be real in valid data), so it is null-bearing only
# when flagged explicitly via DefeatEdge.entails_null. UNDERCUT/RECLASSIFY/REINTERPRET move only
# the warrant/interpretation and never tombstone.
NULL_BEARING_KINDS = frozenset({DefeatEdgeKind.REBUT})


class DefeatEdge(_Model):
    source: str
    target: str
    kind: DefeatEdgeKind
    note: str | None = None
    provisional: bool = False
    entails_null: bool | None = None  # explicit effect-null entailment override (the refund gate)

    @model_validator(mode="after")
    def _no_self_loop(self) -> DefeatEdge:
        if self.source == self.target:
            raise ValueError(
                "a DefeatEdge must relate two DISTINCT claims (no self-defeat/self-support)"
            )
        return self


def effective_defeats(
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
    licensed_ids: frozenset[str] = frozenset(),
) -> frozenset[tuple[str, str]]:
    """(source, target) attack pairs that survive the VAF value filter.

    An attack defeats UNLESS the target strength-dominates the source (Pareto). When
    either strength is absent or the two are incomparable, the attack stands — absence
    of proven superiority is not superiority. `evidence_for` is never a defeat.
    Provisional edges are inert until their source claim appears in `licensed_ids`.
    """
    out: set[tuple[str, str]] = set()
    for e in edges:
        if e.kind not in ATTACK_KINDS:
            continue
        if e.provisional and e.source not in licensed_ids:
            continue  # provisional: inert until its source claim is LICENSED
        s_src = strength.get(e.source)
        s_tgt = strength.get(e.target)
        if s_src is not None and s_tgt is not None and s_tgt.dominates(s_src):
            continue  # target at-least-as-strong on every axis (>=, standard VAF preference) -> attack filtered out
        out.add((e.source, e.target))
    return frozenset(out)


def is_null_bearing(edge: DefeatEdge) -> bool:
    """True iff this defeat's acceptance entails the defeated claim's effect-null, so it may
    refund (tombstone) the e-LOND discovery. `entails_null` overrides the kind default; absent
    it, only REBUT is null-bearing. See evalue-claim-graph/fix-edge-kind-refund.md."""
    if edge.entails_null is not None:
        return edge.entails_null
    return edge.kind in NULL_BEARING_KINDS


def null_bearing_knockout_ids(
    defeated_ids: Iterable[str],
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
    in_set: frozenset[str],
    licensed_ids: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """Of `defeated_ids`, those knocked out by at least one EFFECTIVE, ACCEPTED (grounded-IN
    source), NULL-BEARING defeat — the ONLY claims whose e-LOND discovery may be refunded.
    Warrant-only knockouts (undercut/reinterpret/reclassify) de-license in the graph but keep
    their live discovery (evalue-claim-graph/refund-validity.md §4)."""
    targets = frozenset(defeated_ids)
    edges = tuple(edges)
    effective = effective_defeats(edges, strength, licensed_ids)
    return frozenset(
        e.target
        for e in edges
        if e.target in targets
        and is_null_bearing(e)
        and (e.source, e.target) in effective
        and e.source in in_set
    )


def grounded_extension(
    claim_ids: Iterable[str],
    edges: Iterable[DefeatEdge],
    strength: Mapping[str, StrengthVector | None],
    licensed_ids: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """The IN set under grounded semantics over effective defeats (PTIME least fixpoint).

    F(S) = { a | every effective-attacker of a is itself effectively-attacked by some
    member of S }. Start from the empty set and add acceptable arguments until fixpoint;
    monotone F + add-only => the unique grounded extension. Edge endpoints not in
    claim_ids (e.g. synthetic refutation nodes) participate as nodes.
    """
    defeats = effective_defeats(edges, strength, licensed_ids)
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


def derived_rebut_edges(claims: Iterable[Claim]) -> tuple[DefeatEdge, ...]:
    """Mutual `rebut` edges between LICENSED claims whose conclusions are materially
    incompatible (an L1 `incompatible_with` NeighborEdge resolving between their
    Proposition content_hashes). Opt-in: the caller merges these with authored edges
    before grounded_extension. Reads L1 neighborhoods; mutates nothing.
    """
    licensed = [
        c for c in claims if c.status == Status.LICENSED and c.conclusion is not None
    ]
    by_hash: dict[str, list[str]] = defaultdict(list)
    for c in licensed:
        by_hash[c.conclusion.content_hash].append(c.id)

    edges: list[DefeatEdge] = []
    seen: set[tuple[str, str]] = set()
    for c in licensed:
        for edge in c.conclusion.neighborhood:
            if edge.kind != NeighborEdgeKind.INCOMPATIBLE_WITH:
                continue
            for other_id in by_hash.get(edge.target, ()):
                if other_id == c.id:
                    continue
                for s, t in ((c.id, other_id), (other_id, c.id)):
                    if (s, t) not in seen:
                        seen.add((s, t))
                        edges.append(
                            DefeatEdge(
                                source=s, target=t, kind=DefeatEdgeKind.REBUT,
                                note="derived from incompatible_with",
                            )
                        )
    return tuple(edges)


def undermine_edges_from_failed_satisfactions(
    claim_id: str, satisfactions: Iterable[Satisfaction]
) -> tuple[DefeatEdge, ...]:
    """Failed licensing attempts (L2) become first-class `undermine` edges instead of
    being silently dropped. Each refuted/undetermined Satisfaction yields an edge from
    a synthetic `refutation:{materialization.id}` node attacking the claim's basis.
    """
    failed = {SatisfactionVerdict.REFUTED, SatisfactionVerdict.UNDETERMINED}
    edges: list[DefeatEdge] = []
    for s in satisfactions:
        if s.verdict in failed:
            edges.append(
                DefeatEdge(
                    source=f"refutation:{s.materialization.id}",
                    target=claim_id,
                    kind=DefeatEdgeKind.UNDERMINE,
                    note=f"{s.verdict.value} in {s.materialization.id}",
                )
            )
    return tuple(edges)
