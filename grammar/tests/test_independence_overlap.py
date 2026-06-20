from polymer_grammar import (
    IndependenceTier,
    cohorts_error_independent,
    independence_tier_of,
    max_shared_cause_overlap,
)
from polymer_grammar.licensing import (
    MaterializationContext,
    Satisfaction,
    SatisfactionVerdict,
)


def _sat(dimnames: str, factors: tuple[str, ...] = ()) -> Satisfaction:
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=MaterializationContext(
            id=f"M-{dimnames}", api_version="v1", data_version="d1",
            dimnames_hash=dimnames, shared_cause_factors=factors,
        ),
    )


def test_factors_absent_is_byte_identical_replicated():
    # two distinct cohorts, NO factors -> today's behavior: REPLICATED, indep None
    sats = (_sat("cohortA"), _sat("cohortB"))
    assert cohorts_error_independent(sats) is None
    assert independence_tier_of(sats) is IndependenceTier.REPLICATED
    assert max_shared_cause_overlap(sats) is None


def test_low_overlap_earns_replicated():
    # jaccard({a,b,c},{c,d,e}) = 1/5 = 0.2 < 0.5
    sats = (_sat("cohortA", ("a", "b", "c")), _sat("cohortB", ("c", "d", "e")))
    assert cohorts_error_independent(sats) is True
    assert independence_tier_of(sats) is IndependenceTier.REPLICATED
    assert max_shared_cause_overlap(sats) == 0.2


def test_high_overlap_denies_replicated():
    # jaccard({a,b,c},{a,b,d}) = 2/4 = 0.5 -> NOT < 0.5 -> not independent
    sats = (_sat("cohortA", ("a", "b", "c")), _sat("cohortB", ("a", "b", "d")))
    assert cohorts_error_independent(sats) is False
    assert independence_tier_of(sats) is IndependenceTier.REPRODUCED
    assert max_shared_cause_overlap(sats) == 0.5


def test_partial_factor_adoption_falls_back_to_none():
    # one cohort declares factors, the other does not -> can't assess -> None (byte-identical)
    sats = (_sat("cohortA", ("a", "b")), _sat("cohortB"))
    assert cohorts_error_independent(sats) is None
    assert independence_tier_of(sats) is IndependenceTier.REPLICATED
    assert max_shared_cause_overlap(sats) is None


def test_single_cohort_is_reproduced():
    sats = (_sat("cohortA", ("a",)),)
    assert cohorts_error_independent(sats) is None
    assert independence_tier_of(sats) is IndependenceTier.REPRODUCED


def test_materialization_factors_default_empty():
    m = MaterializationContext(id="M", api_version="v1", data_version="d1")
    assert m.shared_cause_factors == ()
