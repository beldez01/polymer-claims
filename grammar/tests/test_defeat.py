import pytest
from pydantic import ValidationError

from polymer_grammar.defeat import ATTACK_KINDS, DefeatEdge, DefeatEdgeKind


def test_edge_kinds_are_five_attacks_plus_support():
    assert {k.value for k in DefeatEdgeKind} == {
        "undermine", "undercut", "rebut", "reclassify", "reinterpret", "evidence_for",
    }
    assert DefeatEdgeKind.EVIDENCE_FOR not in ATTACK_KINDS
    assert len(ATTACK_KINDS) == 5


def test_edge_is_frozen_and_hashable():
    e = DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT)
    assert isinstance(hash(e), int)
    with pytest.raises(ValidationError):
        DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT, bogus=1)


def test_self_loop_rejected():
    with pytest.raises(ValidationError):
        DefeatEdge(source="a", target="a", kind=DefeatEdgeKind.UNDERMINE)


from polymer_grammar.defeat import effective_defeats
from polymer_grammar.strength import StrengthVector


def _sv(x):
    # uniform vector at level x on all six axes
    return StrengthVector(
        magnitude=x, uncertainty=x, evidence_against_null=x,
        severity=x, world_contact=x, explanatory_virtue=x,
    )


def test_attack_filtered_when_target_dominates_source():
    edges = [DefeatEdge(source="weak", target="strong", kind=DefeatEdgeKind.REBUT)]
    strength = {"weak": _sv(0.2), "strong": _sv(0.9)}
    # target (strong) dominates source (weak) -> attack does NOT defeat
    assert effective_defeats(edges, strength) == frozenset()


def test_attack_stands_when_source_dominates_target():
    edges = [DefeatEdge(source="strong", target="weak", kind=DefeatEdgeKind.REBUT)]
    strength = {"strong": _sv(0.9), "weak": _sv(0.2)}
    assert effective_defeats(edges, strength) == frozenset({("strong", "weak")})


def test_attack_stands_when_incomparable_or_missing_strength():
    # incomparable: a higher on some axis, b higher on another
    a = StrengthVector(magnitude=0.9, uncertainty=0.1, evidence_against_null=0.5,
                       severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    b = StrengthVector(magnitude=0.1, uncertainty=0.9, evidence_against_null=0.5,
                       severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    edges = [DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.UNDERCUT)]
    assert effective_defeats(edges, {"a": a, "b": b}) == frozenset({("a", "b")})
    # missing strength -> attack stands
    assert effective_defeats(edges, {}) == frozenset({("a", "b")})


def test_evidence_for_is_never_a_defeat():
    edges = [DefeatEdge(source="x", target="y", kind=DefeatEdgeKind.EVIDENCE_FOR)]
    assert effective_defeats(edges, {"x": _sv(0.1), "y": _sv(0.9)}) == frozenset()
