import pytest
from pydantic import ValidationError

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import Status


def _leaf():
    return QuantityLeaf(value=-0.238, measurement_basis=MeasurementBasis.DERIVED,
                        formula="ppcor::pcor.test(curvature, co_rate | gc)")


def _lic():
    sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED,
                       materialization=MaterializationContext(
                           id="m1", api_version="0.9.x", data_version="db@2026-06-01"))
    return Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(sat,),
                     rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED)


def _claim(**kw):
    base = dict(id="c", title="t",
                pattern=PatternRef(id="adjusted_effect", version="v1"),
                leaves=[_leaf()], status=Status.LICENSED)
    base.update(kw)
    return Claim(**base)


def test_licensed_claim_without_licensing_still_builds():  # additive back-compat
    assert _claim().licensing is None


def test_licensed_claim_with_licensing_builds():
    c = _claim(licensing=_lic())
    assert c.licensing.route == LicenseRoute.SEVERE_TEST


def test_licensing_on_non_licensed_claim_is_rejected():
    with pytest.raises(ValidationError):
        _claim(status=Status.CONJECTURED, licensing=_lic())


def test_claim_with_licensing_is_hashable():
    assert isinstance(hash(_claim(licensing=_lic())), int)
