"""Task 12 capstone: cross-arm RELATIONS make the spectral layout meaningful.

Deterministic, NO LLM. Mimics today's merged universe — a corpus of mostly EDGELESS
object claims (~96.7% isolated) — then PLANTS a handful of cross-arm relation
meta-claims (`make_relation_claim`) whose relata collectively cover more than half the
nodes. The proof: with no relations the signed-Laplacian graph touches ~0 nodes and the
spectral layout is a bag of hash-ball singletons; with relations the graph connects the
bulk and the eigenmap separates coheres (attraction) from tension (repulsion).

These assertions ARE the end-to-end evidence that relations turn spectral from decorative
into meaningful. They are pure and deterministic (fixed corpus, fixed numpy eigen-solve).
"""
from __future__ import annotations

import math

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    FDRLedger,
    PatternRef,
    RelationKind,
    Status,
    Tier,
    make_relation_claim,
)
from polymer_protocol.corpus import Corpus

from polymer_claims.embedding import build_graph, spectral_layout

_LEDGER = FDRLedger(target_fdr=0.05)
_PATTERN = PatternRef(id="adjusted_effect", version="v1")

# 20 object claims, mimicking the merged universe's isolated bulk.
_OBJECTS = [f"o{i:02d}" for i in range(20)]


def _object_claim(cid: str) -> Claim:
    """An edgeless object claim: no subject, no defeat/equivalence — fully isolated."""
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=Status.EXPLORATORY,
    )


def _coheres(rid: str, src: list[str], tgt: list[str]) -> Claim:
    return make_relation_claim(
        rid, src, tgt, Tier.BIOLOGICAL, RelationKind.COHERES, 1.0,
        rationale=f"coheres {rid}", status=Status.CONJECTURED,
    )


def _tension(rid: str, src: list[str], tgt: list[str]) -> Claim:
    return make_relation_claim(
        rid, src, tgt, Tier.BIOLOGICAL, RelationKind.TENSION, -1.0,
        rationale=f"tension {rid}", status=Status.CONJECTURED,
    )


# Planted cross-arm relations. The first four wire {o00,o01,o02,o03} into one dense
# component (>=4 nodes -> real eigenmap) that carries BOTH a coheres pair (o00~o01) and a
# tension pair (o00~o03) sharing the anchor o00 — so the eigenmap must place the tension
# relatum farther from the anchor than the coheres relatum. The remaining three are
# set-to-set coverage relations that push total node coverage well past 50%.
_RELATIONS = [
    _coheres("rel:o00~o01", ["o00"], ["o01"]),
    _coheres("rel:o00~o02", ["o00"], ["o02"]),
    _tension("rel:o00~o03", ["o00"], ["o03"]),
    _coheres("rel:o01~o02", ["o01"], ["o02"]),
    _coheres("rel:cover-1", ["o04", "o05"], ["o06", "o07"]),
    _coheres("rel:cover-2", ["o08", "o09"], ["o10", "o11"]),
    _coheres("rel:cover-3", ["o12"], ["o13"]),
]


def _corpus(with_relations: bool) -> Corpus:
    claims = tuple(_object_claim(c) for c in _OBJECTS)
    if with_relations:
        claims = claims + tuple(_RELATIONS)
    return Corpus(claims=claims, fdr_ledger=_LEDGER)


def _touched(W) -> set[str]:
    return {node for key in W for node in key}


def test_relation_free_bulk_is_disconnected():
    """The control: 20 edgeless object claims -> the signed-Laplacian graph has NO edges,
    so nothing is touched (the ~3.3%-connected world relations must fix)."""
    ids, W, _ = build_graph(_corpus(with_relations=False))
    assert len(ids) == 20
    assert _touched(W) == set()


def test_relations_connect_the_bulk():
    """Planted relations connect the bulk: the set of nodes touched by any edge in the
    signed-Laplacian graph exceeds half of all nodes (vs 0 in the relation-free control)."""
    ids, W, _ = build_graph(_corpus(with_relations=True))
    touched = _touched(W)
    # 14 object relata (o00..o13) + 7 relation nodes (localized to their relata) = 21 of 27.
    assert len(touched) > 0.5 * len(ids)

    # And far more than the relation-free control (which touches none).
    _, w_free, _ = build_graph(_corpus(with_relations=False))
    assert len(touched) > len(_touched(w_free))


def test_spectral_is_nontrivial_and_separates_tension_from_coheres():
    """Spectral is meaningful: positions are NOT all collapsed to one point, and in the
    dense {o00,o01,o02,o03} component the eigenmap places the TENSION relatum (o03,
    repulsion from o00) strictly farther from the anchor o00 than the COHERES relatum
    (o01, attraction to o00)."""
    pos = spectral_layout(_corpus(with_relations=True))

    # Not all collapsed to a single point.
    assert len({tuple(v) for v in pos.values()}) > 1

    def dist(a: str, b: str) -> float:
        return math.dist(pos[a], pos[b])

    # Repulsion (tension) pushes o03 away from o00; attraction (coheres) pulls o01 in.
    assert dist("o00", "o03") > dist("o00", "o01")
