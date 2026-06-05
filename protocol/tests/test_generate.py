from polymer_grammar import CategoricalLeaf, Claim, DefeatEdge, DefeatEdgeKind, FDRLedger, GenerationMode, Provenance, Status

from polymer_protocol.corpus import Corpus, Proposal
from polymer_protocol.generate import generate_stage
from tests.conftest import _PATTERN, make_claim, make_plan


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
    # self-sourced edges from the (still-unlicensed) proposal claim must be provisional —
    # a non-provisional one is rejected by the C1 trust-boundary backstop in compile_to_IR.
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT, provisional=True)

    def prop(corpus, frontier):
        return (Proposal(operator_id="op", claim=make_claim("b"), edges=(edge,)),)

    out, rec = generate_stage(corp, frontier=(), proposers=(prop,))
    assert "b" in out.by_id()
    assert any(e.source == "b" and e.target == "a" for e in out.defeat_edges)


def test_non_provisional_self_sourced_edge_is_rejected():
    # C1 backstop on the raw proposers= port (not routed through the bridge).
    corp = _corpus([make_claim("a")])
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT, provisional=False)

    def prop(corpus, frontier):
        return (Proposal(operator_id="op", claim=make_claim("b"), edges=(edge,)),)

    out, rec = generate_stage(corp, frontier=(), proposers=(prop,))
    assert "b" not in out.by_id()
    assert {d.claim_id: d.reason for d in rec.discarded}.get("b") == "non-provisional-edge"


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


def test_public_exports():
    import polymer_protocol as p
    for name in ["generate_stage", "compile_to_IR", "Proposal", "GenerationRecord",
                 "DiscardEntry", "rival_generation", "frontier_attack"]:
        assert hasattr(p, name), name


def _const_proposers(n_rival, n_frontier):
    # two toy proposers that emit n isolated CONJECTURED claims each (no edges), distinct ids
    def _mk(op, i):
        return Claim(
            id=f"{op}-{i}",
            title=f"{op}-{i}",
            pattern=_PATTERN,
            leaves=(CategoricalLeaf(ontology_term=f"t-{op}-{i}"),),
            status=Status.CONJECTURED,
            provenance=Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id=op,
                                  method=f"{op}@x", search_cardinality=1),
        )

    def rival(corpus, frontier):
        return tuple(Proposal(operator_id="rival-generation", claim=_mk("rival-generation", i))
                     for i in range(n_rival))

    def frontier_op(corpus, frontier):
        return tuple(Proposal(operator_id="frontier-attack", claim=_mk("frontier-attack", i))
                     for i in range(n_frontier))

    return (rival, frontier_op)


def test_economy_off_is_flat_cap(empty_corpus):
    props = _const_proposers(5, 5)
    corp_a, rec_a = generate_stage(empty_corpus, (), proposers=props, cap=4)
    corp_b, rec_b = generate_stage(empty_corpus, (), proposers=props, cap=4, credit_floor=0.5)  # ledger=None
    assert rec_a.admitted == rec_b.admitted
    assert len(rec_a.admitted) == 4


def test_economy_throttles_low_credit_operator(empty_corpus):
    from polymer_protocol.ledger import OperatorCredit, SelectionLedger
    led = SelectionLedger(credits=(OperatorCredit(operator_id="frontier-attack", n_grounded=0, n_high_eig=4),))
    props = _const_proposers(5, 5)
    corp, rec = generate_stage(empty_corpus, (), proposers=props, cap=6, ledger=led, credit_floor=0.5)
    admitted_ops = [cid.rsplit("-", 1)[0] for cid in rec.admitted]
    assert admitted_ops.count("rival-generation") == 5
    assert admitted_ops.count("frontier-attack") == 1
    op_cap_discards = [d for d in rec.discarded if d.reason == "operator-cap"]
    assert len(op_cap_discards) == 4 and all(d.operator_id == "frontier-attack" for d in op_cap_discards)


def test_exogenous_is_exempt_from_operator_cap(empty_corpus):
    from polymer_protocol.ledger import OperatorCredit, SelectionLedger
    led = SelectionLedger(credits=(OperatorCredit(operator_id="frontier-attack", n_grounded=0, n_high_eig=4),))
    inj = tuple(
        Claim(id=f"inj-{i}", title=f"inj-{i}", pattern=_PATTERN,
              leaves=(CategoricalLeaf(ontology_term=f"t-inj-{i}"),), status=Status.CONJECTURED)
        for i in range(3)
    )
    # Both proposers active so rival-generation (healthy) appears in endo_ops, pushing
    # frontier-attack (below-floor) to its single probation slot. Cap=9 seats all of them.
    corp, rec = generate_stage(empty_corpus, (), proposers=_const_proposers(5, 5), injected=inj,
                               cap=9, ledger=led, credit_floor=0.5)
    assert sum(cid.startswith("inj-") for cid in rec.admitted) == 3
    assert sum(cid.startswith("frontier-attack") for cid in rec.admitted) == 1
