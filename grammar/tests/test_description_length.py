"""Tests for the two-part structural description-length code (MDL meta-tier, Task 1)."""
from __future__ import annotations

from polymer_grammar.claim import Claim
from polymer_grammar.description_length import (
    Schema,
    _corpus_code_length,
    corpus_implied_schema,
    description_length,
)
from polymer_grammar.leaf import CategoricalLeaf, MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import Status

EPSILON = 1e-9


def _qleaf():
    return QuantityLeaf(
        value=-0.238, measurement_basis=MeasurementBasis.DERIVED,
        formula="ppcor::pcor.test(curvature, co_rate | gc)",
    )


def _cleaf(term="GO:0008150"):
    return CategoricalLeaf(ontology_term=term)


def _claim(cid, pattern_id, version="v1", leaves=None):
    return Claim(
        id=cid, title="t",
        pattern=PatternRef(id=pattern_id, version=version),
        leaves=tuple(leaves) if leaves else (_qleaf(),),
        status=Status.CONJECTURED,
    )


def _mixed_corpus():
    # 3 claims: two on P1, one on P2; two distinct categorical ontology terms.
    return (
        _claim("c1", "P1", leaves=(_qleaf(), _cleaf("GO:0008150"))),
        _claim("c2", "P1", leaves=(_qleaf(), _cleaf("GO:0008150"))),
        _claim("c3", "P2", leaves=(_qleaf(), _cleaf("HP:0001250"))),
    )


def test_schema_counts_distinct_patterns_terms():
    claims = _mixed_corpus()
    s = corpus_implied_schema(claims)
    assert isinstance(s, Schema)
    assert len(s.patterns) == 2
    assert s.patterns == frozenset({("P1", "v1"), ("P2", "v1")})
    assert len(s.terms) == 2
    assert s.terms == frozenset({"GO:0008150", "HP:0001250"})
    assert s.constraints == frozenset()


def test_schema_includes_ontology_term_subject_ids():
    from polymer_grammar.subject import OntologyTerm

    subj = OntologyTerm(
        id="MONDO:0005148", display="type 2 diabetes",
        ontology="MONDO", ontology_release="2024", uri="http://x/MONDO_0005148",
    )
    claim = Claim(
        id="cs", title="t", pattern=PatternRef(id="P1", version="v1"),
        leaves=(_qleaf(),), status=Status.CONJECTURED, subject=subj,
    )
    s = corpus_implied_schema((claim,))
    assert "MONDO:0005148" in s.terms


def test_description_length_is_positive_and_deterministic():
    claims = _mixed_corpus()
    s = corpus_implied_schema(claims)
    L1 = description_length(claims, s)
    L2 = description_length(claims, s)
    assert L1 == L2
    assert L1 > 0.0


def test_empty_corpus_is_zero():
    s = corpus_implied_schema(())
    assert description_length((), s) == 0.0
    assert _corpus_code_length((), s) == 0.0


def test_pattern_selector_is_frequency_weighted():
    # all claims share ONE pattern -> zero pattern-selector entropy (-log2(1.0) == 0)
    # vs a corpus split across two patterns -> > 0.
    one = (
        _claim("a1", "P1"),
        _claim("a2", "P1"),
        _claim("a3", "P1"),
        _claim("a4", "P1"),
    )
    split = (
        _claim("b1", "P1"),
        _claim("b2", "P1"),
        _claim("b3", "P2"),
        _claim("b4", "P2"),
    )
    s1 = corpus_implied_schema(one)
    s2 = corpus_implied_schema(split)
    assert _corpus_code_length(one, s1) < _corpus_code_length(split, s2) + EPSILON
    # strictly: the split corpus has nonzero pattern-selector entropy.
    assert _corpus_code_length(one, s1) < _corpus_code_length(split, s2)
