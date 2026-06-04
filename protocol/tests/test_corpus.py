import pytest
from polymer_grammar import (
    DefeatEdge,
    DefeatEdgeKind,
    EquivalenceClaim,
    Status,
)
from pydantic import ValidationError

from polymer_grammar import FDRLedger
from polymer_protocol.corpus import (
    Corpus,
    CycleResult,
    GenerationRecord,
    Proposal,
    SelectionDecision,
    SelectionRecord,
    ValueVector,
)
from polymer_protocol.ledger import SelectionLedger
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


def test_cycle_result_defaults_empty_selection():
    from polymer_grammar import FDRLedger
    from polymer_protocol.corpus import Corpus
    r = CycleResult(corpus=Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)))
    assert r.selection == SelectionRecord()
    assert r.selection.cardinality == 0
    assert r.selection.decisions == ()


def test_selection_record_holds_decisions():
    d = SelectionDecision(claim_id="a", selected=True, value=ValueVector(eig=0.5, stakes=2.0),
                          cost=1.0, rank=0)
    rec = SelectionRecord(decisions=(d,), cardinality=1)
    assert rec.decisions[0].claim_id == "a"
    assert rec.decisions[0].value.eig == 0.5


def test_proposal_holds_claim_and_edges():
    from polymer_grammar import DefeatEdge, DefeatEdgeKind
    c = make_claim("x")
    e = DefeatEdge(source="x", target="y", kind=DefeatEdgeKind.REBUT)
    p = Proposal(operator_id="op", claim=c, edges=(e,))
    assert p.operator_id == "op"
    assert p.claim.id == "x"
    assert p.edges[0].target == "y"


def test_proposal_defaults_no_edges():
    p = Proposal(operator_id="op", claim=make_claim("x"))
    assert p.edges == ()


def test_generation_record_defaults_empty():
    r = GenerationRecord()
    assert r.proposed == 0
    assert r.admitted == ()
    assert r.discarded == ()


def test_cycle_result_defaults_empty_generation():
    res = CycleResult(corpus=Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)))
    assert res.generation == GenerationRecord()


def test_selection_decision_has_cell_and_lane():
    d = SelectionDecision(claim_id="a", selected=True, value=ValueVector(eig=0.5, stakes=1.0),
                          cost=1.0, rank=0, cell="pat|none", lane="reserve")
    assert d.cell == "pat|none"
    assert d.lane == "reserve"


def test_selection_decision_lane_defaults_main():
    d = SelectionDecision(claim_id="a", selected=False, value=ValueVector(), cost=1.0, rank=0)
    assert d.cell == "" and d.lane == "main"


def test_cycle_result_defaults_empty_ledger():
    from polymer_grammar import FDRLedger
    from polymer_protocol.corpus import Corpus, CycleResult
    r = CycleResult(corpus=Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)))
    assert r.ledger == SelectionLedger()
