import pytest

from polymer_grammar.subject import ClaimSetSubject


def test_sorted_and_disjoint_ok():
    s = ClaimSetSubject(id="r1", display="A~B", source_set=("a2", "a1"), target_set=("b1",))
    assert s.kind == "claim_set"
    assert s.source_set == ("a1", "a2")  # canonicalized sorted


def test_overlap_rejected():
    with pytest.raises(ValueError, match="disjoint"):
        ClaimSetSubject(id="r", display="x", source_set=("a",), target_set=("a",))


def test_empty_side_rejected():
    with pytest.raises(ValueError):
        ClaimSetSubject(id="r", display="x", source_set=(), target_set=("b",))
