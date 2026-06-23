"""Deterministic percentile-bootstrap CI for the DEFINITIONAL tier (umbrella-side)."""
from polymer_claims.calibration_stats import bootstrap_mean_ci


def test_bootstrap_is_deterministic_for_fixed_seed():
    vals = [0.04, 0.05, 0.03, 0.06, 0.05, 0.04, 0.07, 0.02]
    a = bootstrap_mean_ci(vals, seed=0)
    b = bootstrap_mean_ci(vals, seed=0)
    assert a == b


def test_bootstrap_ci_brackets_the_mean():
    vals = [0.04, 0.05, 0.03, 0.06, 0.05, 0.04, 0.07, 0.02]
    mean = sum(vals) / len(vals)
    lo, hi = bootstrap_mean_ci(vals, seed=0)
    assert lo is not None and hi is not None
    assert lo <= mean <= hi
    assert lo < hi


def test_bootstrap_none_below_two_values():
    assert bootstrap_mean_ci([0.05]) == (None, None)
    assert bootstrap_mean_ci([]) == (None, None)
