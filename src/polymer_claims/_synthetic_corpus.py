"""Deterministic planted 3-cluster synthetic corpus for relational embedding tests.

Ground truth for the relational graph embedding separation tests.
NO RNG — all structure is planted by construction.

Clusters
--------
c0 — pattern "synth_effect"        8 claims (c0_0 .. c0_7)
c1 — pattern "synth_mediation"     8 claims (c1_0 .. c1_7)
c2 — pattern "synth_dose"          8 claims (c2_0 .. c2_7)

Special structure
-----------------
EQUIV_PAIR  — ("c0_0", "c0_1") linked by EquivalenceClaim inside cluster 0
POLAR_PAIR  — ("c0_2", "c0_3") opposite directions + REBUT DefeatEdge inside cluster 0
ISOLATED    — ["iso_0", "iso_1", "iso_2"] no edges whatsoever

Intra-cluster connectivity
--------------------------
Each cluster is wired densely via a mix of ENTAILS conclusion-neighborhood edges and
EVIDENCE_FOR / REBUT DefeatEdges so every claim touches ≥2 cluster-mates.

Cross-cluster edges
-------------------
Three weak UNDERCUT edges, one per cluster pair, between peripheral claims (never the
equivalence or polar pairs). They make the graph a single weakly-connected component so
the lattice can't trivially separate the clusters — dense intra vs a few weak inter is the
canonical spectral-clustering scenario the eigenmap must resolve.
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    DefeatEdge,
    DefeatEdgeKind,
    Direction,
    EquivalenceClaim,
    FDRLedger,
    NeighborEdge,
    NeighborEdgeKind,
    PatternRef,
    PendingReason,
    Proposition,
    Status,
)
from polymer_protocol.corpus import Corpus

# ── Patterns (one per cluster) ─────────────────────────────────────────────────
_P_EFFECT = PatternRef(id="synth_effect", version="v1")
_P_MEDIATION = PatternRef(id="synth_mediation", version="v1")
_P_DOSE = PatternRef(id="synth_dose", version="v1")

# ── Ground-truth constants ─────────────────────────────────────────────────────
CLUSTERS: dict[str, list[str]] = {
    "c0": [f"c0_{i}" for i in range(8)],
    "c1": [f"c1_{i}" for i in range(8)],
    "c2": [f"c2_{i}" for i in range(8)],
}

EQUIV_PAIR: tuple[str, str] = ("c0_0", "c0_1")
POLAR_PAIR: tuple[str, str] = ("c0_2", "c0_3")
ISOLATED: list[str] = ["iso_0", "iso_1", "iso_2"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _simple_prop(estimand: str, direction: Direction) -> Proposition:
    return Proposition(direction=direction, estimand=estimand, descriptor=estimand)


def _prop_with_entails(
    estimand: str,
    direction: Direction,
    target_hash: str,
    label: str,
) -> Proposition:
    """Proposition whose conclusion ENTAILS another (by content_hash)."""
    return Proposition(
        direction=direction,
        estimand=estimand,
        descriptor=estimand,
        neighborhood=(
            NeighborEdge(
                kind=NeighborEdgeKind.ENTAILS,
                target=target_hash,
                label=label,
            ),
        ),
    )


def _claim(
    cid: str,
    pattern: PatternRef,
    status: Status = Status.EXPLORATORY,
    *,
    conclusion: Proposition | None = None,
) -> Claim:
    pending_reason = PendingReason.CONTESTED if status == Status.PENDING else None
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=pattern,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=status,
        pending_reason=pending_reason,
        conclusion=conclusion,
    )


def _defeat(src: str, tgt: str, kind: DefeatEdgeKind) -> DefeatEdge:
    return DefeatEdge(source=src, target=tgt, kind=kind)


def _entails_pair(
    upstream_estimand: str, downstream_estimand: str, label: str
) -> tuple[Proposition, Proposition]:
    """An (upstream, downstream) proposition pair where upstream's conclusion ENTAILS downstream's.
    Returns (upstream, downstream) — both POSITIVE; `label` is the entails-edge note."""
    downstream = _simple_prop(downstream_estimand, Direction.POSITIVE)
    upstream = _prop_with_entails(
        upstream_estimand, Direction.POSITIVE, downstream.content_hash, label
    )
    return upstream, downstream


# ── Builder ────────────────────────────────────────────────────────────────────

def planted_corpus() -> Corpus:
    """Build and return the planted synthetic corpus.

    All structure — cluster membership, polar pair, equivalence pair, isolated
    claims — is encoded deterministically in the returned Corpus; no RNG used.
    """
    claims: list[Claim] = []
    defeat_edges: list[DefeatEdge] = []
    equivalences: list[EquivalenceClaim] = []

    # ── Cluster 0 — synth_effect ───────────────────────────────────────────────
    #
    # EQUIV_PAIR: c0_0 and c0_1 are near-duplicates linked by EquivalenceClaim.
    # Both have the same estimand/direction so their propositions encode similarity.
    #
    # POLAR_PAIR: c0_2 (POSITIVE) and c0_3 (NEGATIVE) are opposite poles linked
    # by a REBUT DefeatEdge.
    #
    # Intra-cluster wiring:
    #   c0_4.conclusion ENTAILS c0_5.conclusion  (conclusion-neighborhood edge)
    #   c0_6.conclusion ENTAILS c0_7.conclusion  (conclusion-neighborhood edge)
    #   EVIDENCE_FOR edges: c0_0→c0_4, c0_1→c0_5, c0_4→c0_6, c0_5→c0_7
    #   REBUT: c0_2 vs c0_3 (the polar pair)
    #   UNDERCUT: c0_6→c0_3, c0_7→c0_2  (pulls the polar pair into the dense subgraph)
    # Each claim reaches ≥2 cluster-mates.

    # Propositions for the EQUIV_PAIR — identical estimand, same direction
    prop_c0_0 = _simple_prop("synth_effect_core", Direction.POSITIVE)
    prop_c0_1 = _simple_prop("synth_effect_core", Direction.POSITIVE)  # near-duplicate

    # POLAR_PAIR propositions
    prop_c0_2 = _simple_prop("synth_effect_polar", Direction.POSITIVE)
    prop_c0_3 = _simple_prop("synth_effect_polar", Direction.NEGATIVE)

    # c0_4 ENTAILS c0_5; c0_6 ENTAILS c0_7
    prop_c0_4, prop_c0_5 = _entails_pair(
        "synth_effect_upstream", "synth_effect_downstream", "c0_4 => c0_5"
    )
    prop_c0_6, prop_c0_7 = _entails_pair(
        "synth_effect_branch", "synth_effect_leaf", "c0_6 => c0_7"
    )

    claims += [
        _claim("c0_0", _P_EFFECT, Status.LICENSED, conclusion=prop_c0_0),
        _claim("c0_1", _P_EFFECT, Status.LICENSED, conclusion=prop_c0_1),
        _claim("c0_2", _P_EFFECT, Status.PENDING, conclusion=prop_c0_2),
        _claim("c0_3", _P_EFFECT, Status.PENDING, conclusion=prop_c0_3),
        _claim("c0_4", _P_EFFECT, conclusion=prop_c0_4),
        _claim("c0_5", _P_EFFECT, conclusion=prop_c0_5),
        _claim("c0_6", _P_EFFECT, conclusion=prop_c0_6),
        _claim("c0_7", _P_EFFECT, conclusion=prop_c0_7),
    ]

    # Cluster 0 — defeat edges (all intra-cluster)
    defeat_edges += [
        _defeat("c0_2", "c0_3", DefeatEdgeKind.REBUT),        # POLAR_PAIR rebut
        _defeat("c0_0", "c0_4", DefeatEdgeKind.EVIDENCE_FOR), # c0_0 supports c0_4
        _defeat("c0_1", "c0_5", DefeatEdgeKind.EVIDENCE_FOR), # c0_1 supports c0_5
        _defeat("c0_4", "c0_6", DefeatEdgeKind.EVIDENCE_FOR), # c0_4 supports c0_6
        _defeat("c0_5", "c0_7", DefeatEdgeKind.EVIDENCE_FOR), # c0_5 supports c0_7
        _defeat("c0_6", "c0_3", DefeatEdgeKind.UNDERCUT),     # pulls c0_3 into subgraph
        _defeat("c0_7", "c0_2", DefeatEdgeKind.UNDERCUT),     # pulls c0_2 into subgraph
    ]

    # Cluster 0 — equivalence
    equivalences.append(
        EquivalenceClaim(
            id="EQ_c0",
            left=EQUIV_PAIR[0],
            right=EQUIV_PAIR[1],
            severity=0.5,
            status=Status.LICENSED,
        )
    )

    # ── Cluster 1 — synth_mediation ────────────────────────────────────────────
    #
    # Intra-cluster wiring:
    #   c1_2.conclusion ENTAILS c1_3.conclusion
    #   c1_4.conclusion ENTAILS c1_5.conclusion
    #   EVIDENCE_FOR: c1_0→c1_2, c1_1→c1_3, c1_4→c1_0, c1_5→c1_1
    #   REBUT: c1_6→c1_7
    #   UNDERCUT: c1_7→c1_6 (bidirectional tension keeps both in the subgraph)
    #   bridge: c1_6→c1_0, c1_7→c1_1 (so {c1_6,c1_7} join the c1_0..c1_5 body)

    prop_c1_2, prop_c1_3 = _entails_pair(
        "synth_mediation_upstream", "synth_mediation_downstream", "c1_2 => c1_3"
    )
    prop_c1_4, prop_c1_5 = _entails_pair(
        "synth_mediation_branch", "synth_mediation_leaf", "c1_4 => c1_5"
    )

    claims += [
        _claim("c1_0", _P_MEDIATION),
        _claim("c1_1", _P_MEDIATION),
        _claim("c1_2", _P_MEDIATION, conclusion=prop_c1_2),
        _claim("c1_3", _P_MEDIATION, conclusion=prop_c1_3),
        _claim("c1_4", _P_MEDIATION, conclusion=prop_c1_4),
        _claim("c1_5", _P_MEDIATION, conclusion=prop_c1_5),
        _claim("c1_6", _P_MEDIATION),
        _claim("c1_7", _P_MEDIATION),
    ]

    defeat_edges += [
        _defeat("c1_0", "c1_2", DefeatEdgeKind.EVIDENCE_FOR),
        _defeat("c1_1", "c1_3", DefeatEdgeKind.EVIDENCE_FOR),
        _defeat("c1_4", "c1_0", DefeatEdgeKind.EVIDENCE_FOR),
        _defeat("c1_5", "c1_1", DefeatEdgeKind.EVIDENCE_FOR),
        _defeat("c1_6", "c1_7", DefeatEdgeKind.REBUT),
        _defeat("c1_7", "c1_6", DefeatEdgeKind.UNDERCUT),
        # bridge {c1_6, c1_7} into the c1_0..c1_5 body (else c1 fragments)
        _defeat("c1_6", "c1_0", DefeatEdgeKind.UNDERCUT),
        _defeat("c1_7", "c1_1", DefeatEdgeKind.UNDERCUT),
    ]

    # ── Cluster 2 — synth_dose ────────────────────────────────────────────────
    #
    # Intra-cluster wiring:
    #   c2_2.conclusion ENTAILS c2_3.conclusion
    #   c2_4.conclusion ENTAILS c2_5.conclusion
    #   EVIDENCE_FOR: c2_0→c2_2, c2_1→c2_3, c2_4→c2_0, c2_5→c2_1
    #   REBUT: c2_6→c2_7
    #   UNDERCUT: c2_7→c2_6
    #   bridge: c2_6→c2_0, c2_7→c2_1 (so {c2_6,c2_7} join the c2_0..c2_5 body)

    prop_c2_2, prop_c2_3 = _entails_pair(
        "synth_dose_upstream", "synth_dose_downstream", "c2_2 => c2_3"
    )
    prop_c2_4, prop_c2_5 = _entails_pair(
        "synth_dose_branch", "synth_dose_leaf", "c2_4 => c2_5"
    )

    claims += [
        _claim("c2_0", _P_DOSE),
        _claim("c2_1", _P_DOSE),
        _claim("c2_2", _P_DOSE, conclusion=prop_c2_2),
        _claim("c2_3", _P_DOSE, conclusion=prop_c2_3),
        _claim("c2_4", _P_DOSE, conclusion=prop_c2_4),
        _claim("c2_5", _P_DOSE, conclusion=prop_c2_5),
        _claim("c2_6", _P_DOSE),
        _claim("c2_7", _P_DOSE),
    ]

    defeat_edges += [
        _defeat("c2_0", "c2_2", DefeatEdgeKind.EVIDENCE_FOR),
        _defeat("c2_1", "c2_3", DefeatEdgeKind.EVIDENCE_FOR),
        _defeat("c2_4", "c2_0", DefeatEdgeKind.EVIDENCE_FOR),
        _defeat("c2_5", "c2_1", DefeatEdgeKind.EVIDENCE_FOR),
        _defeat("c2_6", "c2_7", DefeatEdgeKind.REBUT),
        _defeat("c2_7", "c2_6", DefeatEdgeKind.UNDERCUT),
        # bridge {c2_6, c2_7} into the c2_0..c2_5 body (else c2 fragments)
        _defeat("c2_6", "c2_0", DefeatEdgeKind.UNDERCUT),
        _defeat("c2_7", "c2_1", DefeatEdgeKind.UNDERCUT),
    ]

    # ── Weak inter-cluster links ───────────────────────────────────────────────
    # Three weak UNDERCUT edges, one per cluster pair, between PERIPHERAL claims
    # (never the equivalence pair c0_0/c0_1 nor the polar pair c0_2/c0_3). These
    # make the graph a single weakly-connected component, so the lattice can no
    # longer trivially separate the clusters — the spectral eigenmap must. Dense
    # intra (entails 0.9 / evidence_for 0.8 / equivalence 1.0) vs a few weak inter
    # (undercut 0.5) is the canonical spectral-clustering scenario.
    defeat_edges += [
        _defeat("c0_7", "c1_0", DefeatEdgeKind.UNDERCUT),
        _defeat("c1_6", "c2_0", DefeatEdgeKind.UNDERCUT),
        _defeat("c2_7", "c0_4", DefeatEdgeKind.UNDERCUT),
    ]

    # ── Isolated claims ────────────────────────────────────────────────────────
    # No edges at all — must not appear in any TopologyEdge.
    for iso_id in ISOLATED:
        claims.append(_claim(iso_id, _P_EFFECT))

    return Corpus(
        claims=tuple(claims),
        defeat_edges=tuple(defeat_edges),
        equivalences=tuple(equivalences),
        fdr_ledger=FDRLedger(target_fdr=0.05),
    )


# Reveal order for the dense cluster-0 subgraph (see planted_corpus): each prefix is a valid
# Corpus whose largest connected component grows 2 -> 3 -> 4 -> 7 -> 8, crossing the n>=4 eigenmap
# threshold so the signed-Laplacian basis genuinely recomputes/flips between frames.
_CLUSTER0_REVEAL = ("c0_0", "c0_1", "c0_2", "c0_3", "c0_4", "c0_5", "c0_6", "c0_7")


def growing_cluster0_corpora() -> list[Corpus]:
    """A deterministic sequence of growing sub-corpora built from planted_corpus's c0_* cluster.

    Each step reveals one more claim (starting from the first 4) and keeps only the defeat edges /
    equivalences whose endpoints are present, so every sub-corpus validates. Used to demonstrate
    the Procrustes anti-thrash mechanism on a genuinely growing >=4-node component (the default
    serve seed caps at a 3-node component and never reaches the eigenmap)."""
    pc = planted_corpus()
    by_id = {c.id: c for c in pc.claims}
    out: list[Corpus] = []
    for k in range(4, len(_CLUSTER0_REVEAL) + 1):
        present = set(_CLUSTER0_REVEAL[:k])
        sub_defeat = tuple(
            e for e in pc.defeat_edges if e.source in present and e.target in present
        )
        sub_equiv = tuple(
            e for e in pc.equivalences if e.left in present and e.right in present
        )
        out.append(
            Corpus(
                claims=tuple(by_id[i] for i in _CLUSTER0_REVEAL[:k]),
                fdr_ledger=pc.fdr_ledger,
                defeat_edges=sub_defeat,
                equivalences=sub_equiv,
            )
        )
    return out
