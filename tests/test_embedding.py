from __future__ import annotations

import math

from polymer_claims.embedding import spectral_layout
from polymer_claims._synthetic_corpus import planted_corpus
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
