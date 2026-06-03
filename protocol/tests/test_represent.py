from polymer_grammar import DefeatEdge, DefeatEdgeKind, StrengthVector

from polymer_protocol.corpus import Corpus
from polymer_protocol.represent import represent
from tests.conftest import make_claim


def test_no_attacks_everyone_in_extension_empty_frontier(empty_ledger):
    corpus = Corpus(claims=(make_claim("a"), make_claim("b")), fdr_ledger=empty_ledger)
    scaffolding = represent(corpus)
    assert scaffolding.grounded_extension == ("a", "b")
    assert scaffolding.frontier == ()


def test_effective_attack_puts_target_on_frontier(empty_ledger):
    # b attacks a; neither has strength, so the attack is effective -> a is OUT, on frontier.
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(
        claims=(make_claim("a"), make_claim("b")),
        defeat_edges=(edge,),
        fdr_ledger=empty_ledger,
    )
    scaffolding = represent(corpus)
    assert "b" in scaffolding.grounded_extension
    assert "a" not in scaffolding.grounded_extension
    assert scaffolding.frontier == ("a",)


def test_target_dominates_source_attack_filtered_out(empty_ledger):
    strong = StrengthVector(magnitude=0.9, uncertainty=0.9, evidence_against_null=0.9,
                            severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    weak = StrengthVector(magnitude=0.1, uncertainty=0.1, evidence_against_null=0.1,
                          severity=0.1, world_contact=0.1, explanatory_virtue=0.1)
    edge = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)
    corpus = Corpus(
        claims=(make_claim("a", strength=strong), make_claim("b", strength=weak)),
        defeat_edges=(edge,),
        fdr_ledger=empty_ledger,
    )
    scaffolding = represent(corpus)
    # a strength-dominates b, so b's attack is filtered: a stays IN, frontier empty.
    assert scaffolding.grounded_extension == ("a", "b")
    assert scaffolding.frontier == ()


def test_synthetic_source_does_not_appear_in_outputs(empty_ledger):
    # Grammar produces "refutation:<id>" nodes (undermine_edges_from_failed_satisfactions).
    # They must not leak into the scaffolding output, which contains only claim ids.
    edge = DefeatEdge(source="refutation:M1", target="a", kind=DefeatEdgeKind.UNDERMINE)
    corpus = Corpus(
        claims=(make_claim("a"), make_claim("b")),
        defeat_edges=(edge,),
        fdr_ledger=empty_ledger,
    )
    scaffolding = represent(corpus)
    assert "refutation:M1" not in scaffolding.grounded_extension
    assert "refutation:M1" not in scaffolding.frontier
    # a is attacked by a synthetic source with no defender -> a is OUT and on the frontier
    assert scaffolding.frontier == ("a",)
