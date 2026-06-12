from __future__ import annotations

import itertools
import math

from polymer_claims._synthetic_corpus import CLUSTERS, EQUIV_PAIR, POLAR_PAIR, planted_corpus
from polymer_claims.embedding import spectral_layout
from polymer_grammar import FDRLedger
from polymer_protocol.corpus import Corpus


def test_spectral_layout_is_deterministic():
    corpus = planted_corpus()
    a = spectral_layout(corpus)
    b = spectral_layout(corpus)
    assert a == b  # byte-identical (sign-canonicalized + rounded)


def test_every_claim_gets_a_finite_position():
    corpus = planted_corpus()
    pos = spectral_layout(corpus)
    assert set(pos) == {c.id for c in corpus.claims}
    for xyz in pos.values():
        assert len(xyz) == 3
        assert all(math.isfinite(v) for v in xyz)


def test_empty_corpus_returns_empty():
    assert spectral_layout(Corpus(claims=(), fdr_ledger=FDRLedger(target_fdr=0.05))) == {}


def test_positions_are_in_unit_cube():
    pos = spectral_layout(planted_corpus())
    for xyz in pos.values():
        assert all(-1.0001 <= v <= 1.0001 for v in xyz)


def _dist(p, q):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p, q)))


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def test_clusters_separate_intra_below_inter():
    pos = spectral_layout(planted_corpus())
    intra = [
        _dist(pos[a], pos[b])
        for ids in CLUSTERS.values()
        for a, b in itertools.combinations(ids, 2)
    ]
    cls = list(CLUSTERS.values())
    inter = [
        _dist(pos[a], pos[b])
        for i in range(len(cls))
        for j in range(i + 1, len(cls))
        for a in cls[i]
        for b in cls[j]
    ]
    mean_intra, mean_inter = _mean(intra), _mean(inter)
    assert mean_intra < mean_inter
    assert (mean_inter - mean_intra) / mean_inter > 0.25  # silhouette-style margin


def test_polar_pair_near_but_not_coincident():
    pos = spectral_layout(planted_corpus())
    d_polar = _dist(pos[POLAR_PAIR[0]], pos[POLAR_PAIR[1]])
    cls = list(CLUSTERS.values())
    inter = [_dist(pos[a], pos[b]) for a in cls[0] for b in cls[1]]
    assert 0.0 < d_polar < _mean(inter)  # near (same cluster) but separated (rebut)


def test_equivalence_pair_is_very_close():
    pos = spectral_layout(planted_corpus())
    d_eq = _dist(pos[EQUIV_PAIR[0]], pos[EQUIV_PAIR[1]])
    d_polar = _dist(pos[POLAR_PAIR[0]], pos[POLAR_PAIR[1]])
    assert d_eq < d_polar  # equivalence is the tightest relation in the cluster
