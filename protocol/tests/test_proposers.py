from polymer_grammar import (
    Comparator,
    ComputeGraph,
    DefeatEdge,
    DefeatEdgeKind,
    Direction,
    EvaluationPlan,
    FDRLedger,
    MeasurementBasis,
    OperationNode,
    PendingReason,
    ProducedLeafSpec,
    Proposition,
    SatisfactionCriterion,
    Status,
    grounded_extension,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.cycle import run_cycle
from polymer_protocol.proposers import frontier_attack, rival_generation
from tests.conftest import make_claim, make_plan


def _corpus(claims):
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


def _concl(direction):
    return Proposition(direction=direction, estimand="beta", descriptor="X on Y")


def test_rival_emits_other_two_directions():
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE))
    props = rival_generation(_corpus([c]), ())
    dirs = {p.claim.conclusion.direction for p in props}
    assert dirs == {Direction.NEGATIVE, Direction.NULL}
    assert all(p.claim.status == Status.CONJECTURED for p in props)


def test_rival_has_empty_neighborhood():
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE))
    props = rival_generation(_corpus([c]), ())
    for p in props:
        assert p.claim.conclusion.neighborhood == ()  # isolated — no incompatible_with edge


def test_rival_generation_is_belief_neutral_through_run_cycle(ctx, adapters):
    # rival_generation through a full run_cycle must NOT retract the pre-existing claim
    c = make_claim("c", conclusion=Proposition(direction=Direction.POSITIVE, estimand="b", descriptor="d"))
    corp = Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05))
    result = run_cycle(corp, adapters, ctx, proposers=(rival_generation,))
    assert "c" in result.corpus.by_id()  # pre-existing claim SURVIVES (not retracted)


def test_rival_skips_claims_without_conclusion():
    c = make_claim("c")  # no conclusion
    assert rival_generation(_corpus([c]), ()) == ()


def test_rival_skips_its_own_output():
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE))
    props = rival_generation(_corpus([c]), ())
    rival = props[0].claim
    props2 = rival_generation(_corpus([c, rival]), ())
    # the fed-back rival spawns nothing; only original c's 2 rivals appear, same ids
    assert {p.claim.id for p in props2} == {p.claim.id for p in props}


def test_rival_ids_are_deterministic():
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE))
    a = {p.claim.id for p in rival_generation(_corpus([c]), ())}
    b = {p.claim.id for p in rival_generation(_corpus([c]), ())}
    assert a == b


def _corpus_e(claims, edges):
    return Corpus(claims=tuple(claims), defeat_edges=tuple(edges),
                  fdr_ledger=FDRLedger(target_fdr=0.05))


def test_frontier_attack_emits_provisional_rebut_edge():
    from polymer_grammar import DefeatEdgeKind
    a, b = make_claim("a"), make_claim("b")
    edges = (DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),)
    props = frontier_attack(_corpus_e([a, b], edges), frontier=("a",))
    assert len(props) == 1
    p = props[0]
    assert p.claim.status == Status.CONJECTURED and p.claim.conclusion is None
    assert len(p.edges) == 1
    e = p.edges[0]
    assert e.source == p.claim.id and e.target == "b"
    assert e.kind == DefeatEdgeKind.REBUT and e.provisional is True


def test_frontier_attack_is_belief_neutral():
    # planting D must NOT change the grounded extension of the existing claims
    a, b = make_claim("a"), make_claim("b")
    edges = (DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),)
    corp = _corpus_e([a, b], edges)
    strength = {c.id: c.strength for c in corp.claims}
    before = grounded_extension([c.id for c in corp.claims], corp.defeat_edges, strength)
    p = frontier_attack(corp, ("a",))[0]
    # fold the seed in (no new edges) and recompute over the augmented claim set
    claims2 = corp.claims + (p.claim,)
    strength2 = {c.id: c.strength for c in claims2}
    after = grounded_extension([c.id for c in claims2], corp.defeat_edges + p.edges, strength2)
    # membership of the ORIGINAL claims is unchanged (D may be newly IN, but a/b unchanged)
    assert (after & {"a", "b"}) == (before & {"a", "b"})


def test_frontier_attack_skips_synthetic_sources():
    a = make_claim("a")
    edges = (DefeatEdge(source="refutation:x", target="a", kind=DefeatEdgeKind.UNDERMINE),)
    assert frontier_attack(_corpus_e([a], edges), frontier=("a",)) == ()


def test_frontier_attack_deterministic_ids():
    a, b = make_claim("a"), make_claim("b")
    edges = (DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),)
    corp = _corpus_e([a, b], edges)
    assert frontier_attack(corp, ("a",))[0].claim.id == frontier_attack(corp, ("a",))[0].claim.id


def test_rival_emits_provisional_rebut_edge_to_source():
    from polymer_grammar import DefeatEdgeKind
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE))
    props = rival_generation(_corpus([c]), ())
    for p in props:
        assert p.claim.conclusion.neighborhood == ()       # still no incompatible_with
        assert len(p.edges) == 1
        e = p.edges[0]
        assert e.source == p.claim.id and e.target == "c"
        assert e.kind == DefeatEdgeKind.REBUT and e.provisional is True


def test_rival_of_planned_source_is_executable():
    plan = make_plan(0.09, 0.05, Comparator.LT)  # source criterion: value < threshold
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE), plan=plan)
    props = rival_generation(_corpus([c]), ())
    assert props  # two rivals (negative, null)
    for p in props:
        assert p.claim.status == Status.PENDING
        assert p.claim.pending_reason == PendingReason.UNTESTED
        assert p.claim.evaluation_plan is not None
        assert p.claim.evaluation_plan.graph.content_hash == plan.graph.content_hash  # graph reused verbatim
        assert p.claim.evaluation_plan.criterion.comparator == Comparator.GE          # LT mirrored -> GE
        assert len(p.edges) == 1 and p.edges[0].target == "c"
        assert p.edges[0].provisional is True


def test_rival_of_within_tol_source_stays_conjectured():
    node = OperationNode(
        id="n0",
        impl="builtin::const",
        params=(("value", "0.09"),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.WITHIN_TOL, threshold=0.05, tolerance=0.1),
    )
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE), plan=plan)
    props = rival_generation(_corpus([c]), ())
    assert props
    for p in props:
        assert p.claim.status == Status.CONJECTURED
        assert p.claim.evaluation_plan is None
        assert len(p.edges) == 1 and p.edges[0].provisional is True
