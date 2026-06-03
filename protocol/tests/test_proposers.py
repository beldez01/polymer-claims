from polymer_grammar import (
    DefeatEdge, DefeatEdgeKind, Direction, FDRLedger, NeighborEdgeKind, Proposition, Status,
    grounded_extension,
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


def test_frontier_attack_emits_seed_without_edge():
    a, b = make_claim("a"), make_claim("b")
    edges = (DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),)
    props = frontier_attack(_corpus_e([a, b], edges), frontier=("a",))
    assert len(props) == 1
    p = props[0]
    assert p.claim.status == Status.CONJECTURED
    assert p.claim.conclusion is None
    assert p.edges == ()                      # NO edge — belief-neutral


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
