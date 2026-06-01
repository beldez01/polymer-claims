"""Deep-immutability hardening: list fields -> tuples, so Claim/Pattern are
genuinely immutable and hashable for content-addressing (spec §3.2)."""
import pytest

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef, get_pattern
from polymer_grammar.status import Status


def _leaf():
    return QuantityLeaf(
        value=-0.238, measurement_basis=MeasurementBasis.DERIVED,
        formula="ppcor::pcor.test(curvature, co_rate | gc)",
    )


def _claim(**kw):
    base = dict(
        id="c", title="t",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=[_leaf()],  # passed as a list literal — must coerce to tuple
        status=Status.CONJECTURED,
    )
    base.update(kw)
    return Claim(**base)


def test_claim_leaves_coerced_to_tuple_and_immutable():
    c = _claim()
    assert isinstance(c.leaves, tuple)
    with pytest.raises(AttributeError):
        c.leaves.append(_leaf())  # tuple has no append


def test_claim_is_hashable_for_content_addressing():
    assert isinstance(hash(_claim()), int)


def test_equal_claims_hash_equal():
    assert hash(_claim()) == hash(_claim())


def test_pattern_list_fields_are_tuples_and_immutable():
    p = get_pattern("adjusted_effect", "v1")
    assert isinstance(p.intended_applications, tuple)
    assert isinstance(p.excluded_applications, tuple)
    assert isinstance(p.merged_from, tuple)
    with pytest.raises(AttributeError):
        p.merged_from.append("x")


def test_pattern_is_hashable():
    assert isinstance(hash(get_pattern("adjusted_effect", "v1")), int)
