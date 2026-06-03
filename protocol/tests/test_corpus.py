import pytest
from polymer_grammar import (
    DefeatEdge,
    DefeatEdgeKind,
    EquivalenceClaim,
    Status,
)
from pydantic import ValidationError

from polymer_protocol.corpus import Corpus
from tests.conftest import make_claim


def test_corpus_by_id_indexes_claims(empty_ledger):
    a, b = make_claim("a"), make_claim("b")
    corpus = Corpus(claims=(a, b), fdr_ledger=empty_ledger)
    assert corpus.by_id() == {"a": a, "b": b}


def test_corpus_rejects_duplicate_claim_ids(empty_ledger):
    with pytest.raises(ValidationError, match="unique"):
        Corpus(claims=(make_claim("a"), make_claim("a")), fdr_ledger=empty_ledger)


def test_corpus_rejects_dangling_defeat_target(empty_ledger):
    edge = DefeatEdge(source="a", target="ghost", kind=DefeatEdgeKind.REBUT)
    with pytest.raises(ValidationError, match="ghost"):
        Corpus(claims=(make_claim("a"),), defeat_edges=(edge,), fdr_ledger=empty_ledger)


def test_corpus_allows_synthetic_defeat_source(empty_ledger):
    # refutation:<id> synthetic source is produced by the grammar; must be permitted.
    edge = DefeatEdge(source="refutation:M1", target="a", kind=DefeatEdgeKind.UNDERMINE)
    corpus = Corpus(claims=(make_claim("a"),), defeat_edges=(edge,), fdr_ledger=empty_ledger)
    assert corpus.defeat_edges == (edge,)


def test_corpus_rejects_dangling_equivalence_endpoint(empty_ledger):
    eq = EquivalenceClaim(id="e1", left="a", right="ghost", severity=1.0, status=Status.LICENSED)
    with pytest.raises(ValidationError, match="ghost"):
        Corpus(claims=(make_claim("a"),), equivalences=(eq,), fdr_ledger=empty_ledger)


def test_corpus_is_frozen(empty_ledger):
    corpus = Corpus(claims=(make_claim("a"),), fdr_ledger=empty_ledger)
    with pytest.raises(ValidationError):
        corpus.claims = ()
