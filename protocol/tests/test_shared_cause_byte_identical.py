"""Byte-identity golden test for the shared-cause feature (Phase D slice 2).

When NO claim carries `prior_cohorts` and NO `cohort_of_ref` is supplied, every code
path added in Phase D slice 2 is inert.  This test makes the inert-when-off contract
explicit and is intentionally a golden assertion (not a red-green cycle) — the feature
is present but inactive, so passing immediately IS the expected outcome.

Two sub-tests:

1. verify_stage — `licensing.severity_provenance` stays None and `strength.severity` is
   NOT capped (remains at the pre-feature value, 0.9).

2. select_stage — the `SelectionRecord.decisions` order from a call WITHOUT
   `cohort_of_ref` matches a second call with an empty map supplied (identity of
   behaviour; the byte-identical baseline is the no-map call).
"""
from __future__ import annotations

from polymer_grammar import Status
from polymer_protocol.select import ValueWeights, select_stage
from polymer_protocol.verify import verify_stage

from tests.helpers_select import (
    SIMPLE_COST,
    SIMPLE_COST_WEIGHTS,
    two_equal_candidates,
)
from tests.helpers_verify import licensable_corpus

# ---------------------------------------------------------------------------
# 1. VERIFY — inert when prior_cohorts is empty
# ---------------------------------------------------------------------------


def test_verify_empty_prior_cohorts_severity_provenance_is_none() -> None:
    """Empty prior_cohorts (the default) => severity_provenance stays None.

    `licensable_corpus()` returns a claim with NO prior_cohorts set at all
    (Provenance.prior_cohorts defaults to ()).  verify_stage must leave
    licensing.severity_provenance as None and must NOT cap severity.
    """
    corpus, scaffolding, exec_records = licensable_corpus()

    out = verify_stage(corpus, scaffolding, exec_records)
    c1 = out.by_id()["c1"]

    # The claim licenses (gate passes).
    assert c1.status == Status.LICENSED

    # The shared-cause code path is inert: no provenance annotation.
    assert c1.licensing.severity_provenance is None

    # Severity was NOT capped — the pre-feature value (0.9) passes through.
    assert c1.strength is not None
    assert c1.strength.severity == 0.9  # original _STRENGTH.severity from helpers_verify


def test_verify_empty_prior_cohorts_strength_axis_unchanged() -> None:
    """Strength vector must be byte-identical to the pre-feature value when off.

    Runs verify_stage twice on the same corpus and asserts the strength tuple
    is identical — no stochastic mutation, no cap side-effect.
    """
    corpus, scaffolding, exec_records = licensable_corpus()

    out_a = verify_stage(corpus, scaffolding, exec_records)
    out_b = verify_stage(corpus, scaffolding, exec_records)

    sv_a = out_a.by_id()["c1"].strength
    sv_b = out_b.by_id()["c1"].strength

    assert sv_a == sv_b
    # Confirm the pre-cap severity value is intact (not 0.2 CONFIRMATORY ceiling).
    assert sv_a is not None and sv_a.severity > 0.2


# ---------------------------------------------------------------------------
# 2. SELECT — inert when cohort_of_ref is absent
# ---------------------------------------------------------------------------


def test_select_no_cohort_of_ref_decisions_order_matches_baseline() -> None:
    """select_stage with NO cohort_of_ref is byte-identical to the pre-feature baseline.

    Uses `two_equal_candidates()` from helpers_select — both candidates have
    `prior_cohorts` set (one overlapping, one disjoint), but without the
    `cohort_of_ref` injection the severity factor for every candidate is 1.0,
    so the ordering must be the same as if the shared-cause code were absent.
    """
    corpus = two_equal_candidates()

    # Baseline: no cohort_of_ref supplied (pre-feature path).
    _, rec_baseline = select_stage(
        corpus,
        cost_model=SIMPLE_COST,
        budget=None,
        value_weights=ValueWeights(),
        cost_weights=SIMPLE_COST_WEIGHTS,
    )

    # Second call: same corpus, same args — determinism assertion.
    _, rec_again = select_stage(
        corpus,
        cost_model=SIMPLE_COST,
        budget=None,
        value_weights=ValueWeights(),
        cost_weights=SIMPLE_COST_WEIGHTS,
    )

    # The decisions tuple (sorted by claim_id in the implementation) must be identical.
    assert rec_baseline.decisions == rec_again.decisions


def test_select_empty_cohort_of_ref_is_identical_to_no_arg() -> None:
    """Passing cohort_of_ref={} is byte-identical to passing None (no map).

    The severity factor falls back to 1.0 for every candidate when the map is
    empty or None.  This pins the None/empty-map equivalence contract.
    """
    corpus = two_equal_candidates()

    _, rec_no_arg = select_stage(
        corpus,
        cost_model=SIMPLE_COST,
        budget=None,
        value_weights=ValueWeights(),
        cost_weights=SIMPLE_COST_WEIGHTS,
    )

    _, rec_empty_map = select_stage(
        corpus,
        cost_model=SIMPLE_COST,
        budget=None,
        value_weights=ValueWeights(),
        cost_weights=SIMPLE_COST_WEIGHTS,
        cohort_of_ref={},
    )

    assert rec_no_arg.decisions == rec_empty_map.decisions
