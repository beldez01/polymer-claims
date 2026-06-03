from polymer_grammar import (
    DefeatEdge, DefeatEdgeKind, Direction, FDRLedger, NeighborEdgeKind, Proposition, Status,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.proposers import frontier_attack, rival_generation
from tests.conftest import make_claim


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


def test_rival_marks_incompatible_with_source():
    c = make_claim("c", conclusion=_concl(Direction.POSITIVE))
    props = rival_generation(_corpus([c]), ())
    for p in props:
        ne = p.claim.conclusion.neighborhood
        assert len(ne) == 1
        assert ne[0].kind == NeighborEdgeKind.INCOMPATIBLE_WITH
        assert ne[0].target == c.conclusion.content_hash


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


def test_frontier_attack_emits_defense_and_edge():
    # b attacks a; a is on the frontier -> emit D that rebuts b
    a, b = make_claim("a"), make_claim("b")
    edges = (DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),)
    props = frontier_attack(_corpus_e([a, b], edges), frontier=("a",))
    assert len(props) == 1
    p = props[0]
    assert p.claim.status == Status.CONJECTURED
    assert p.claim.strength is None  # inert: cannot defeat b until licensed
    assert len(p.edges) == 1
    assert p.edges[0].source == p.claim.id and p.edges[0].target == "b"
    assert p.edges[0].kind == DefeatEdgeKind.REBUT


def test_frontier_attack_skips_synthetic_sources():
    # an undermine edge from a failed satisfaction has a synthetic ":" source
    a = make_claim("a")
    edges = (DefeatEdge(source="refutation:x", target="a", kind=DefeatEdgeKind.UNDERMINE),)
    props = frontier_attack(_corpus_e([a], edges), frontier=("a",))
    assert props == ()


def test_frontier_attack_deterministic_ids():
    a, b = make_claim("a"), make_claim("b")
    edges = (DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),)
    corp = _corpus_e([a, b], edges)
    id1 = frontier_attack(corp, ("a",))[0].claim.id
    id2 = frontier_attack(corp, ("a",))[0].claim.id
    assert id1 == id2
