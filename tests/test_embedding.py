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


def test_spectral_sample_file_is_valid_and_nontrivial():
    import json
    from pathlib import Path
    from polymer_protocol.topology import TopologyExport

    p = Path(__file__).resolve().parents[1] / "viewer" / "public" / "sample-topology-spectral.json"
    export = TopologyExport.model_validate(json.loads(p.read_text()))
    assert export.layout_id == "external:spectral-v1"
    assert len(export.nodes) > 10
    assert any(any(v != 0.0 for v in n.position) for n in export.nodes)


def test_sign_canonicalization_is_flip_invariant():
    import numpy as np
    from polymer_claims.embedding import _canonicalize_columns
    M = np.array([
        [0.5, -0.5, 0.1],
        [0.5,  0.5, -0.2],
        [-0.5, 0.5,  0.3],
        [-0.5, -0.5, -0.4],
    ])
    base = _canonicalize_columns(M.copy())
    # flipping the sign of any input columns must NOT change the canonical output
    flipped = _canonicalize_columns(M * np.array([-1.0, 1.0, -1.0]))
    assert np.allclose(base, flipped)


def test_procrustes_align_recovers_rotation_and_reflection():
    import numpy as np
    from polymer_claims.embedding import procrustes_align

    # 4 non-coplanar points (rank-3 → recovery is exact)
    prev = {
        "a": (0.1, 0.2, 0.3),
        "b": (-0.4, 0.5, -0.1),
        "c": (0.7, -0.2, 0.6),
        "d": (-0.3, -0.5, 0.2),
    }
    # An orthogonal matrix with det = -1 (a rotation composed with a reflection)
    G = np.array([
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, -1.0],
    ])
    assert round(float(np.linalg.det(G)), 6) == -1.0
    new = {k: tuple(np.asarray(v) @ G) for k, v in prev.items()}

    aligned = procrustes_align(prev, new)

    assert set(aligned) == set(prev)
    for k in prev:
        for got, want in zip(aligned[k], prev[k]):
            assert abs(got - want) < 1e-6


def test_procrustes_align_underdetermined_returns_new_unchanged():
    from polymer_claims.embedding import procrustes_align

    # fewer than 2 common ids → nothing to align to → new returned unchanged
    assert procrustes_align({}, {"x": (1.0, 2.0, 3.0)}) == {"x": (1.0, 2.0, 3.0)}
    assert procrustes_align({"a": (0.0, 0.0, 0.0)}, {"b": (1.0, 1.0, 1.0)}) == {"b": (1.0, 1.0, 1.0)}


def test_procrustes_align_transforms_new_only_nodes():
    """Nodes in new but not in prev must receive the same orthogonal transform."""
    import numpy as np
    from polymer_claims.embedding import procrustes_align

    prev = {"a": (1.0, 0.0, 0.0), "b": (0.0, 1.0, 0.0), "c": (0.0, 0.0, 1.0)}
    G = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])  # 90° about z
    new = {k: tuple(float(x) for x in np.asarray(v) @ G) for k, v in prev.items()}
    new["d"] = tuple(float(x) for x in np.asarray([0.707, 0.707, 0.0]) @ G)

    aligned = procrustes_align(prev, new)

    # new["d"] lives in the rotated (new) frame; the recovered transform must carry it back into
    # prev's frame, i.e. apply G.T (the inverse of G) to the value actually stored in new["d"].
    expected_d = tuple(round(float(x), 6) for x in np.asarray(new["d"]) @ G.T)
    assert aligned["d"] == expected_d
