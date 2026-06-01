from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.roles import CausalRoles
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


def test_claim_without_roles_still_builds():  # back-compat
    assert _claim().roles is None


def test_claim_with_roles_builds_and_exposes_adjustment_set():
    roles = CausalRoles(predictor="curvature", outcome="crossover_rate",
                        confounders=("gc_content",))
    c = _claim(roles=roles)
    assert c.roles.adjustment_set == frozenset({"gc_content"})


def test_claim_with_roles_is_hashable():
    roles = CausalRoles(predictor="x", outcome="y")
    assert isinstance(hash(_claim(roles=roles)), int)
