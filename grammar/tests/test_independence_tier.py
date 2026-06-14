from __future__ import annotations

import pytest

from polymer_grammar import (
    IndependenceTier,
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
    independence_tier_of,
)


def _sat(dimnames: str | None, mid: str = "M") -> Satisfaction:
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=MaterializationContext(
            id=mid, api_version="v1", data_version="d1", dimnames_hash=dimnames
        ),
    )


def test_default_tier_is_reproduced():
    lic = Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(_sat("hA"),),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
    )
    assert lic.independence_tier is IndependenceTier.REPRODUCED


def test_tier_of_single_cohort_is_reproduced():
    assert independence_tier_of((_sat("hA"),)) is IndependenceTier.REPRODUCED


def test_tier_of_two_distinct_cohorts_is_replicated():
    assert independence_tier_of((_sat("hA"), _sat("hB", "M2"))) is IndependenceTier.REPLICATED


def test_tier_of_two_same_cohort_is_reproduced():
    assert independence_tier_of((_sat("hA"), _sat("hA", "M2"))) is IndependenceTier.REPRODUCED


def test_tier_of_none_dimnames_is_reproduced():
    # back-compat: pre-CES claims carry dimnames_hash=None -> never REPLICATED
    assert independence_tier_of((_sat(None), _sat(None, "M2"))) is IndependenceTier.REPRODUCED


def test_replicated_field_requires_two_distinct_cohorts():
    with pytest.raises(ValueError, match="distinct dimnames_hash"):
        Licensing(
            route=LicenseRoute.SEVERE_TEST,
            satisfactions=(_sat("hA"), _sat("hA", "M2")),
            rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
            independence_tier=IndependenceTier.REPLICATED,
        )


def test_replicated_field_accepts_two_distinct_cohorts():
    lic = Licensing(
        route=LicenseRoute.SEVERE_TEST,
        satisfactions=(_sat("hA"), _sat("hB", "M2")),
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
        independence_tier=IndependenceTier.REPLICATED,
    )
    assert lic.independence_tier is IndependenceTier.REPLICATED
