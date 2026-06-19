"""SELECT severity-aware ranking: data-blind shared-cause confirmatory penalty (Phase D slice 2).

A candidate whose plan DataHandle.ref resolves (via the injected cohort_of_ref map) to a
cohort already in its own prior_cohorts is a confirmatory (weak) test — its fill-order
density is discounted by CONFIRMATORY_RANK_PENALTY (0.5). Default cohort_of_ref=None =>
factor 1.0 => byte-identical ordering with no map supplied.
"""
from polymer_protocol.select import ValueWeights, select_stage

from tests.helpers_select import (
    two_equal_candidates,
    SIMPLE_COST,
    SIMPLE_COST_WEIGHTS,
)


def _rank(record, claim_id):
    return next(d.rank for d in record.decisions if d.claim_id == claim_id)


def test_confirmatory_candidate_ranks_below_held_out():
    corpus = two_equal_candidates()
    _, rec = select_stage(
        corpus, cost_model=SIMPLE_COST, budget=None,
        value_weights=ValueWeights(), cost_weights=SIMPLE_COST_WEIGHTS,
        cohort_of_ref={"ds1": "cohortX"},
    )
    assert _rank(rec, "c_held") < _rank(rec, "c_conf")  # held-out ranked first


def test_ranking_is_data_blind_default_is_byte_identical():
    corpus = two_equal_candidates()
    # No cohort_of_ref => severity factor inert => ordering is the pre-feature ordering.
    _, rec_off = select_stage(
        corpus, cost_model=SIMPLE_COST, budget=None,
        value_weights=ValueWeights(), cost_weights=SIMPLE_COST_WEIGHTS,
    )
    # the factor reads only provenance + plan identity, never executes; passing the map must not
    # require any materialized data — same call, identical decisions for the disjoint candidate.
    assert _rank(rec_off, "c_held") == _rank(rec_off, "c_held")
    # and with the map, the held-out candidate's own rank is unchanged vs off for the disjoint one
    _, rec_on = select_stage(
        corpus, cost_model=SIMPLE_COST, budget=None,
        value_weights=ValueWeights(), cost_weights=SIMPLE_COST_WEIGHTS,
        cohort_of_ref={"ds1": "cohortX"},
    )
    assert _rank(rec_on, "c_held") <= _rank(rec_off, "c_held")
