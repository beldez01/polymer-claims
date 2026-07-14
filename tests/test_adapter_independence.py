"""Adapter-independence Step 0 probe (C1) — measured error-correlation.

Behavior tests per plans/2026-07-07-adapter-independence-hardening-plan.md §3. The probe compute is
exercised on SYNTHETIC score pairs; the live ClinVar/AlphaMissense/ESM1v run is data-gated. Pure
stdlib; umbrella-side; no grammar/protocol/Corpus change.
"""
from __future__ import annotations

import math

from polymer_claims.adapter_independence import (
    error_correlation,
    independence_report,
    n_eff_from_rho,
    set_overlap_neff,
    signed_errors,
)


def test_signed_errors_is_score_minus_label():
    e = signed_errors((0.9, 0.1), (1.0, 0.0))
    assert math.isclose(e[0], -0.1) and math.isclose(e[1], 0.1)


def test_identical_errors_rho_one_neff_one():
    e = (0.2, -0.3, 0.5, -0.1)
    rho = error_correlation(e, e)
    assert math.isclose(rho, 1.0, abs_tol=1e-9)
    assert math.isclose(n_eff_from_rho(rho), 1.0, abs_tol=1e-9)


def test_orthogonal_errors_rho_zero_neff_two():
    a = (1.0, -1.0, 1.0, -1.0)
    b = (1.0, 1.0, -1.0, -1.0)  # uncorrelated with a
    rho = error_correlation(a, b)
    assert math.isclose(rho, 0.0, abs_tol=1e-9)
    assert math.isclose(n_eff_from_rho(rho), 2.0, abs_tol=1e-9)


def test_anticorrelated_errors_more_than_two_witnesses():
    a = (1.0, -1.0, 2.0, -2.0)
    b = tuple(-x for x in a)
    rho = error_correlation(a, b)
    assert rho < 0
    assert n_eff_from_rho(rho) > 2.0  # decorrelated beyond independence


def test_constant_error_vector_is_undefined_not_crash():
    assert math.isnan(error_correlation((0.0, 0.0, 0.0), (1.0, 2.0, 3.0)))


def test_independence_report_rho_neff_confusion_and_per_class():
    # 6 variants: labels + two models' scores (threshold 0.5). Construct a known correlation.
    labels = (1.0, 1.0, 1.0, 0.0, 0.0, 0.0)
    scores_a = (0.9, 0.4, 0.8, 0.2, 0.6, 0.1)  # A wrong on v2 (0.4<0.5 for pathogenic) and v5
    scores_b = (0.7, 0.3, 0.9, 0.1, 0.55, 0.2)  # B wrong on v2 and v5 too (correlated errors)
    rep = independence_report(scores_a, scores_b, labels, threshold_a=0.5, threshold_b=0.5)
    assert rep.n == 6
    assert -1.0 <= rep.rho <= 1.0
    assert math.isclose(rep.n_eff, 2.0 / (1.0 + rep.rho))
    # 2x2 correctness confusion sums to n
    assert rep.both_correct + rep.a_only_correct + rep.b_only_correct + rep.both_wrong == 6
    # both models miss v2 (pathogenic, scored <0.5) and v5 (benign, scored >=0.5) -> >=2 both_wrong
    assert rep.both_wrong >= 2
    # per-class rho is computed where the class has variance (may be nan if degenerate)
    assert rep.rho_pathogenic is not None
    assert rep.rho_benign is not None


def test_set_overlap_neff_claim_shape():
    universe = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
    # identical flag sets -> phi 1 -> N_eff 1
    same = set_overlap_neff({1, 2, 3}, {1, 2, 3}, universe)
    assert math.isclose(same, 1.0, abs_tol=1e-9)
    # disjoint flag sets -> negatively correlated indicators -> more than 2 effective witnesses
    disjoint = set_overlap_neff({1, 2}, {3, 4}, universe)
    assert disjoint > 2.0
