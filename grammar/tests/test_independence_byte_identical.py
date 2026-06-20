"""
Byte-identity golden test for independence_tier_of.

Asserts that with NO shared_cause_factors declared, independence_tier_of is
byte-identical to the pre-§E §2E behavior:

  - Two distinct cohorts (no factors) -> REPLICATED
  - One cohort            (no factors) -> REPRODUCED
  - Same cohort twice     (no factors) -> REPRODUCED

This passes immediately because the §E common-cause gate is *inert when off* —
that IS the point of a byte-identity test. It pins the invariant: adding
shared_cause_factors is purely additive and never silently changes behavior for
callers who do not opt in.
"""

from polymer_grammar import IndependenceTier, independence_tier_of
from polymer_grammar.licensing import (
    MaterializationContext,
    Satisfaction,
    SatisfactionVerdict,
)


def _sat(dimnames):
    return Satisfaction(
        verdict=SatisfactionVerdict.SATISFIED,
        materialization=MaterializationContext(
            id=f"M-{dimnames}", api_version="v1", data_version="d1", dimnames_hash=dimnames,
        ),
    )


def test_two_distinct_cohorts_no_factors_is_replicated():
    # the §2E contract pre-§E: distinct dimnames + no factors -> REPLICATED (byte-identical)
    assert independence_tier_of((_sat("A"), _sat("B"))) is IndependenceTier.REPLICATED


def test_one_cohort_is_reproduced():
    assert independence_tier_of((_sat("A"),)) is IndependenceTier.REPRODUCED


def test_same_cohort_twice_is_reproduced():
    assert independence_tier_of((_sat("A"), _sat("A"))) is IndependenceTier.REPRODUCED
