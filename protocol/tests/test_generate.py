from polymer_grammar import DefeatEdge, DefeatEdgeKind, FDRLedger, Status

from polymer_protocol.corpus import Corpus, Proposal
from polymer_protocol.generate import generate_stage
from tests.conftest import make_claim, make_plan


def _corpus(claims, edges=()):
    return Corpus(claims=tuple(claims), defeat_edges=tuple(edges),
                  fdr_ledger=FDRLedger(target_fdr=0.05))


def test_no_proposers_is_noop():
    corp = _corpus([make_claim("a")])
    out, rec = generate_stage(corp, frontier=())
    assert out is corp           # identity preserved when nothing admitted
    assert rec.proposed == 0
    assert rec.admitted == ()


def test_bus_admits_a_valid_proposal():
    corp = _corpus([make_claim("a")])

    def prop(corpus, frontier):
        return (Proposal(operator_id="op", claim=make_claim("b")),)

    out, rec = generate_stage(corp, frontier=(), proposers=(prop,))
    assert set(out.by_id()) == {"a", "b"}
    assert rec.admitted == ("b",)
    assert rec.proposed == 1


def test_duplicate_id_is_discarded():
    corp = _corpus([make_claim("a")])

    def prop(corpus, frontier):
        return (Proposal(operator_id="op", claim=make_claim("a")),)

    out, rec = generate_stage(corp, frontier=(), proposers=(prop,))
    assert out is corp
    assert rec.admitted == ()
    assert rec.discarded[0].reason == "duplicate"


def test_unresolved_edge_is_discarded():
    corp = _corpus([make_claim("a")])
    edge = DefeatEdge(source="b", target="ghost", kind=DefeatEdgeKind.REBUT)

    def prop(corpus, frontier):
        return (Proposal(operator_id="op", claim=make_claim("b"), edges=(edge,)),)

    out, rec = generate_stage(corp, frontier=(), proposers=(prop,))
    assert out is corp
    assert rec.discarded[0].reason == "unresolved-edge"


def test_invalid_edge_source_is_discarded():
    corp = _corpus([make_claim("a")])
    # edge source is neither the new claim "b" nor a synthetic ":" source
    bad = DefeatEdge(source="not_b", target="a", kind=DefeatEdgeKind.REBUT)

    def prop(corpus, frontier):
        return (Proposal(operator_id="op", claim=make_claim("b"), edges=(bad,)),)

    out, rec = generate_stage(corp, frontier=(), proposers=(prop,))
    assert out is corp
    assert rec.discarded[0].reason == "invalid-edge-source"


def test_admitted_edge_is_added():
    corp = _corpus([make_claim("a")])
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)

    def prop(corpus, frontier):
        return (Proposal(operator_id="op", claim=make_claim("b"), edges=(edge,)),)

    out, rec = generate_stage(corp, frontier=(), proposers=(prop,))
    assert "b" in out.by_id()
    assert any(e.source == "b" and e.target == "a" for e in out.defeat_edges)


def test_injected_claim_gets_provenance_and_admitted():
    corp = _corpus([make_claim("a")])
    injected = make_claim("inj", status=Status.PENDING, plan=make_plan(0.01, 0.05))  # provenance None
    out, rec = generate_stage(corp, frontier=(), injected=(injected,))
    assert "inj" in out.by_id()
    assert out.by_id()["inj"].provenance is not None  # IMPORTED stamped


def test_generation_cap_truncates():
    corp = _corpus([make_claim("a")])

    def prop(corpus, frontier):
        return (
            Proposal(operator_id="op", claim=make_claim("b")),
            Proposal(operator_id="op", claim=make_claim("c")),
        )

    out, rec = generate_stage(corp, frontier=(), proposers=(prop,), cap=1)
    assert len(rec.admitted) == 1
    assert any(d.reason == "cap" for d in rec.discarded)
