from polymer_grammar import SHARED_CAUSE_TAU, shared_cause_jaccard


def test_jaccard_identical_is_one():
    assert shared_cause_jaccard(("a", "b"), ("a", "b")) == 1.0


def test_jaccard_disjoint_is_zero():
    assert shared_cause_jaccard(("a", "b"), ("c", "d")) == 0.0


def test_jaccard_partial():
    # {a,b,c} ∩ {b,c,d} = {b,c} (2); ∪ = {a,b,c,d} (4) -> 0.5
    assert shared_cause_jaccard(("a", "b", "c"), ("b", "c", "d")) == 0.5


def test_jaccard_both_empty_is_zero():
    assert shared_cause_jaccard((), ()) == 0.0


def test_jaccard_one_empty_is_zero():
    assert shared_cause_jaccard(("a",), ()) == 0.0


def test_jaccard_ignores_duplicates_and_order():
    assert shared_cause_jaccard(("a", "a", "b"), ("b", "a")) == 1.0


def test_tau_default():
    assert SHARED_CAUSE_TAU == 0.5
