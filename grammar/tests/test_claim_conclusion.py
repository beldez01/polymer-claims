from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.proposition import Direction, Proposition
from polymer_grammar.status import Status


def _leaf():
    return QuantityLeaf(value=-0.238, measurement_basis=MeasurementBasis.DERIVED,
                        formula="ppcor::pcor.test(curvature, co_rate | gc)")


def _claim(**kw):
    base = dict(id="c", title="t",
                pattern=PatternRef(id="adjusted_effect", version="v1"),
                leaves=[_leaf()], status=Status.CONJECTURED)
    base.update(kw)
    return Claim(**base)


def test_claim_without_conclusion_still_builds():  # Phase-1 back-compat
    assert _claim().conclusion is None


def test_claim_with_conclusion_builds():
    prop = Proposition(direction=Direction.NEGATIVE, estimand="adjusted_effect_size",
                       descriptor="curvature disfavors crossover after GC control")
    c = _claim(conclusion=prop)
    assert c.conclusion is prop
    assert c.conclusion.direction == Direction.NEGATIVE


def test_claim_with_conclusion_is_still_hashable():
    prop = Proposition(direction=Direction.NULL, estimand="x", descriptor="d")
    assert isinstance(hash(_claim(conclusion=prop)), int)
