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


# --- Task 2: transport + mdl_delta + novelty_residual + clears_mdl_bar ------------------------

from polymer_grammar.description_length import (  # noqa: E402
    RevisionDiscovery,
    _PATTERN_BITS,
    classify,
    clears_mdl_bar,
    mdl_delta,
    novelty_residual,
    transport,
)
from polymer_grammar.representation import (  # noqa: E402
    OntologyTermTarget,
    PatternTarget,
    RepresentationRevision,
    RevisionOperation,
)

_refA = PatternRef(id="A", version="v1")
_refB = PatternRef(id="B", version="v1")
_refNew = PatternRef(id="brand_new", version="v1")


def _dup_corpus():
    # patterns A,B identical-signature, each used 5x.
    return tuple(
        _claim(f"a{i}", "A") for i in range(5)
    ) + tuple(_claim(f"b{i}", "B") for i in range(5))


def test_transport_merge_repoints_and_quotients_schema():
    claims = _dup_corpus()
    s = corpus_implied_schema(claims)
    rev = RepresentationRevision(
        operation=RevisionOperation.MERGE,
        target=PatternTarget(patterns=(_refA, _refB)), rationale="dup",
    )
    c2, s2 = transport(claims, s, rev)
    # every claim now points at the unified ref; members gone from schema.
    unified_ids = {c.pattern.id for c in c2}
    assert unified_ids == {"merged:A+B"}
    assert ("A", "v1") not in s2.patterns and ("B", "v1") not in s2.patterns
    assert ("merged:A+B", "v1") in s2.patterns


def test_redundant_merge_compresses_and_is_consolidation():
    claims = _dup_corpus()
    s = corpus_implied_schema(claims)
    rev = RepresentationRevision(
        operation=RevisionOperation.MERGE,
        target=PatternTarget(patterns=(_refA, _refB)), rationale="dup",
    )
    delta = mdl_delta(claims, s, rev)
    assert delta < 0.0                                  # pays for itself
    assert novelty_residual(claims, s, rev) < EPSILON   # generator-reachable -> consolidation
    assert classify(delta, novelty_residual(claims, s, rev)) == "consolidation"


def test_unused_add_costs_bits():
    claims = _dup_corpus()
    s = corpus_implied_schema(claims)
    rev = RepresentationRevision(
        operation=RevisionOperation.ADD,
        target=PatternTarget(patterns=(_refNew,)), rationale="x",
    )
    delta = mdl_delta(claims, s, rev)
    assert delta > 0.0                                  # pure schema cost, nothing uses it
    # a brand-new ADD pattern is not generator-reachable -> full residual.
    assert novelty_residual(claims, s, rev) == _PATTERN_BITS
    assert classify(delta, novelty_residual(claims, s, rev)) == "rejected"


def test_unused_add_ontology_term_costs_bits():
    # The corpus already carries >=2 distinct terms (T>=2), so adding an unused term moves the
    # log*(T) schema count out of its flat n<=1 region -> a strictly positive, unused cost.
    claims = (
        _claim("t1", "A", leaves=(_qleaf(), _cleaf("GO:0008150"))),
        _claim("t2", "A", leaves=(_qleaf(), _cleaf("HP:0001250"))),
    )
    s = corpus_implied_schema(claims)
    rev = RepresentationRevision(
        operation=RevisionOperation.ADD,
        target=OntologyTermTarget(term_id="HP:9999999"), rationale="x",
    )
    assert mdl_delta(claims, s, rev) > 0.0


def test_loadbearing_deprecate_is_rejected():
    claims = _dup_corpus()  # pattern A is load-bearing (5 claims)
    s = corpus_implied_schema(claims)
    rev = RepresentationRevision(
        operation=RevisionOperation.DEPRECATE,
        target=PatternTarget(patterns=(_refA,)), rationale="x",
    )
    assert mdl_delta(claims, s, rev) > 0.0              # generic re-encoding costs more


def test_relax_is_mdl_deferred():
    claims = _dup_corpus()
    s = corpus_implied_schema(claims)
    from polymer_grammar.representation import ConstraintTarget
    rev = RepresentationRevision(
        operation=RevisionOperation.RELAX,
        target=ConstraintTarget(name="at_least_one_exclusion"), rationale="x",
    )
    c2, s2 = transport(claims, s, rev)
    assert c2 == claims and s2 == s
    assert mdl_delta(claims, s, rev) == 0.0


def test_clears_mdl_bar_threshold():
    assert clears_mdl_bar(-5.0) is True
    assert clears_mdl_bar(-0.0001) is False             # below _MDL_EPS
    assert clears_mdl_bar(0.0) is False


def test_mdl_delta_is_deterministic():
    claims = _dup_corpus()
    s = corpus_implied_schema(claims)
    rev = RepresentationRevision(
        operation=RevisionOperation.MERGE,
        target=PatternTarget(patterns=(_refA, _refB)), rationale="dup",
    )
    assert mdl_delta(claims, s, rev) == mdl_delta(claims, s, rev)


def test_revision_discovery_record():
    rec = RevisionDiscovery(mdl_delta=-3.0, novelty_residual=0.0, classification="consolidation")
    assert rec.classification == "consolidation"


# --- Review fix: ontology-term DEPRECATE coherence + reachability hardening -------------------

from polymer_grammar.description_length import (  # noqa: E402
    _GENERIC_TERM_ID,
    _claim_terms,
)


def _term_corpus_t3():
    # T=3 distinct in-use terms; the target term is load-bearing (used by 2 claims).
    return (
        _claim("u1", "A", leaves=(_qleaf(), _cleaf("GO:0008150"))),
        _claim("u2", "A", leaves=(_qleaf(), _cleaf("GO:0008150"))),
        _claim("u3", "A", leaves=(_qleaf(), _cleaf("HP:0001250"))),
        _claim("u4", "A", leaves=(_qleaf(), _cleaf("MONDO:0005148"))),
    )


def test_deprecate_inuse_term_is_rejected():
    # deprecating a load-bearing (still-in-use) term must RAISE cost, not look like free compression.
    claims = _term_corpus_t3()
    s = corpus_implied_schema(claims)
    rev = RepresentationRevision(
        operation=RevisionOperation.DEPRECATE,
        target=OntologyTermTarget(term_id="GO:0008150"), rationale="x",
    )
    assert mdl_delta(claims, s, rev) > 0.0
    assert not clears_mdl_bar(mdl_delta(claims, s, rev))


def test_deprecate_unused_term_does_not_raise_cost():
    # deprecating a term NOT used by any claim is at most a schema saving (<= the in-use case).
    claims = _term_corpus_t3()
    s = corpus_implied_schema(claims)
    rev_unused = RepresentationRevision(
        operation=RevisionOperation.DEPRECATE,
        target=OntologyTermTarget(term_id="EFO:9999999"), rationale="x",  # absent from corpus
    )
    rev_inuse = RepresentationRevision(
        operation=RevisionOperation.DEPRECATE,
        target=OntologyTermTarget(term_id="GO:0008150"), rationale="x",
    )
    assert mdl_delta(claims, s, rev_unused) < mdl_delta(claims, s, rev_inuse)
    assert mdl_delta(claims, s, rev_unused) <= 0.0


def test_deprecate_term_keeps_code_coherent():
    # after transport, every term emitted in L_corpus must be declared in the post-transport schema
    # (no dangling term used by a claim but absent from schema.terms).
    claims = _term_corpus_t3()
    s = corpus_implied_schema(claims)
    rev = RepresentationRevision(
        operation=RevisionOperation.DEPRECATE,
        target=OntologyTermTarget(term_id="GO:0008150"), rationale="x",
    )
    c2, s2 = transport(claims, s, rev)
    used_terms = set()
    for c in c2:
        used_terms.update(_claim_terms(c))
    # the generic-term sentinel is priced internally, not declared; every OTHER used term is declared.
    dangling = {t for t in used_terms if t != _GENERIC_TERM_ID and t not in s2.terms}
    assert dangling == set()
    # the deprecated term no longer appears in any claim's selectors.
    assert "GO:0008150" not in used_terms


def test_add_pattern_literally_named_merged_is_still_rejected():
    # hardening: an ADD of a pattern whose id starts with "merged:" must NOT be misread as a quotient.
    claims = _dup_corpus()
    s = corpus_implied_schema(claims)
    rev = RepresentationRevision(
        operation=RevisionOperation.ADD,
        target=PatternTarget(patterns=(PatternRef(id="merged:foo", version="v1"),)),
        rationale="x",
    )
    # unused ADD still costs bits -> rejected, regardless of the misleading name.
    assert mdl_delta(claims, s, rev) > 0.0
    assert classify(mdl_delta(claims, s, rev), novelty_residual(claims, s, rev)) == "rejected"
