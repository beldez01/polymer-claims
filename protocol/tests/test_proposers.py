from polymer_grammar import (
    Direction, FDRLedger, NeighborEdgeKind, Proposition, Status,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.proposers import rival_generation
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
