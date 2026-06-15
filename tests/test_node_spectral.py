"""Spectral live layout: Procrustes anti-thrash on a growing >=4-node component (the mechanism),
plus NodeRunner integration over the default seed (layout_id / positions / determinism / evolution),
force byte-identity, and graceful fallback when the numpy embedder is absent."""
from __future__ import annotations

import sys

from polymer_claims.node import NodeRunner
from polymer_claims.seed import default_seed_corpus
from polymer_claims._synthetic_corpus import growing_cluster0_corpora


def _max_consecutive_disp(seq):
    """Max per-node displacement on common nodes across consecutive id->position dicts."""
    m = 0.0
    for a, b in zip(seq, seq[1:]):
        for nid in a.keys() & b.keys():
            d = sum((x - y) ** 2 for x, y in zip(a[nid], b[nid])) ** 0.5
            m = max(m, d)
    return m


def test_procrustes_kills_eigenbasis_thrash_on_growing_component():
    # AC#2 (mechanism): over a corpus whose connected component grows across the n>=4 eigenmap
    # threshold, the Procrustes-aligned chain has strictly smaller (with margin) and bounded
    # consecutive displacement than the raw per-frame eigenmap — i.e. the alignment kills the
    # eigenbasis sign/rotation thrash. Deterministic (sign-canonicalised eigenmap + SVD + 6dp).
    # NOTE: this exercises the mechanism directly, NOT via NodeRunner.tick(), because the default
    # serve seed never grows a >=4 component (see the plan's design note); AC#3 below covers the
    # NodeRunner integration path.
    from polymer_claims.embedding import spectral_layout, procrustes_align

    corpora = growing_cluster0_corpora()
    raw = [spectral_layout(c) for c in corpora]
    aligned = [raw[0]]
    prev = raw[0]
    for r in raw[1:]:
        a = procrustes_align(prev, r)
        aligned.append(a)
        prev = a

    raw_max = _max_consecutive_disp(raw)
    aligned_max = _max_consecutive_disp(aligned)

    # Non-vacuous: the raw eigenmap must actually thrash (the basis flips as the component grows).
    assert raw_max > 0.5, f"corpus did not exercise eigenbasis thrash (raw_max={raw_max})"
    # Strictly smaller, with comfortable margin (measured ~1.27 vs ~2.70).
    assert aligned_max < 0.75 * raw_max, f"alignment margin too small: {aligned_max} vs {raw_max}"


def test_aligned_chain_is_deterministic():
    # The Procrustes chain is deterministic for a fixed corpus sequence (byte-stable).
    from polymer_claims.embedding import spectral_layout, procrustes_align

    def chain():
        corpora = growing_cluster0_corpora()
        raw = [spectral_layout(c) for c in corpora]
        out = [raw[0]]
        prev = raw[0]
        for r in raw[1:]:
            a = procrustes_align(prev, r)
            out.append(a)
            prev = a
        return out

    assert chain() == chain()


def test_spectral_nodeRunner_frame_is_external_and_nonorigin():
    # AC#3 (integration): a spectral-mode NodeRunner frame is tagged external:spectral-v1 with
    # meaningful (non-origin) positions, and the corpus still evolves (licensing is layout-blind).
    corpus, kwargs = default_seed_corpus()
    runner = NodeRunner.from_seed(corpus, layout="spectral", **kwargs)
    for _ in range(8):
        runner.tick()
    tl = runner.snapshot()

    last = tl.frames[-1]
    assert last.topology.layout_id == "external:spectral-v1"
    assert any(any(abs(c) > 1e-9 for c in n.position) for n in last.topology.nodes)
    assert tl.frames[-1].stats.n_licensed >= tl.frames[0].stats.n_licensed


def test_spectral_nodeRunner_is_deterministic():
    # Two identical spectral runs produce byte-identical timelines (determinism through the runner).
    def run():
        corpus, kwargs = default_seed_corpus()
        r = NodeRunner.from_seed(corpus, layout="spectral", **kwargs)
        for _ in range(6):
            r.tick()
        return r.snapshot().model_dump_json()

    assert run() == run()


def test_force_layout_is_fruchterman_reingold():
    # AC#4: layout="force" produces the historical FR layout_id (byte-identical force path).
    corpus, kwargs = default_seed_corpus()
    runner = NodeRunner.from_seed(corpus, layout="force", **kwargs)
    runner.tick()
    assert runner.frames[-1].topology.layout_id.startswith("fruchterman-reingold")


def test_spectral_falls_back_to_force_without_embedder(monkeypatch):
    # Graceful fallback: if the lazy embedder import fails, spectral mode uses the force path and
    # records the actual (FR) layout_id. Setting the module to None makes `import` raise ImportError.
    monkeypatch.setitem(sys.modules, "polymer_claims.embedding", None)
    corpus, kwargs = default_seed_corpus()
    runner = NodeRunner.from_seed(corpus, layout="spectral", **kwargs)
    assert runner.frames[0].topology.layout_id.startswith("fruchterman-reingold")
