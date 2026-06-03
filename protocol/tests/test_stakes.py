from polymer_grammar import DefeatEdge, DefeatEdgeKind, FDRLedger, Status

from polymer_protocol.corpus import Corpus
from polymer_protocol.stakes import dependency_cone, stakes
from tests.conftest import make_claim


def _corpus(claims, edges=()):
    return Corpus(claims=tuple(claims), defeat_edges=tuple(edges), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_isolated_claim_has_empty_cone():
    c = make_claim("a")
    corp = _corpus([c])
    assert dependency_cone(corp, "a") == frozenset()
    assert stakes(corp, "a") == 0.0


def test_cone_follows_defeat_edges_transitively():
    a, b, d = make_claim("a"), make_claim("b"), make_claim("d")
    edges = (
        DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="b", target="d", kind=DefeatEdgeKind.REBUT),
    )
    corp = _corpus([a, b, d], edges)
    assert dependency_cone(corp, "a") == frozenset({"b", "d"})
    assert stakes(corp, "a") == 2.0  # b, d both non-LICENSED -> weight 1 each


def test_licensed_dependents_weighted_higher():
    a = make_claim("a")
    b = make_claim("b", status=Status.LICENSED)
    edges = (DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT),)
    corp = _corpus([a, b], edges)
    assert stakes(corp, "a") == 2.0  # one LICENSED dependent at weight 2.0


def test_cone_excludes_self():
    a, b = make_claim("a"), make_claim("b")
    edges = (DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT),)
    corp = _corpus([a, b], edges)
    assert "a" not in dependency_cone(corp, "a")
