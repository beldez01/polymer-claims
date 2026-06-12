from __future__ import annotations

from polymer_claims.embedding import KIND_WEIGHT, build_graph
from polymer_claims._synthetic_corpus import planted_corpus


def test_kind_weights_match_spec():
    assert KIND_WEIGHT["equivalence"] == 1.0
    assert KIND_WEIGHT["entails"] == 0.9
    assert KIND_WEIGHT["evidence_for"] == 0.8
    assert KIND_WEIGHT["undermine"] == KIND_WEIGHT["undercut"] == 0.5
    assert KIND_WEIGHT["reclassify"] == KIND_WEIGHT["reinterpret"] == 0.5
    assert KIND_WEIGHT["rebut"] == 0.4


def test_build_graph_weights_and_symmetry():
    corpus = planted_corpus()
    node_ids, W, polar = build_graph(corpus)
    assert set(node_ids) == {c.id for c in corpus.claims}
    for key, w in W.items():
        assert isinstance(key, frozenset) and len(key) == 2
        assert w in set(KIND_WEIGHT.values())


def test_polar_flags_opposite_direction_rebut():
    corpus = planted_corpus()
    _, _, polar = build_graph(corpus)
    # the planted corpus has a positive-vs-negative rebut pair (POLAR_PAIR) -> flagged polar
    from polymer_claims._synthetic_corpus import POLAR_PAIR
    assert frozenset(POLAR_PAIR) in polar
