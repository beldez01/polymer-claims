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
