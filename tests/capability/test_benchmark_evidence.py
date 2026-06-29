"""Test suite for paired_advantage_evalue."""
import pytest
import numpy as np
from polymer_claims.benchmark_evidence import paired_advantage_evalue


def test_strong_stream():
    """Strong stream of 1.0 should produce e-value > 32.9."""
    result = paired_advantage_evalue([1.0] * 40, theta0=0.0)
    assert result > 32.9


def test_all_ties():
    """All-ties (zeros) should produce e-value ≈ 1.0."""
    result = paired_advantage_evalue([0.0] * 40, theta0=0.0)
    assert np.isclose(result, 1.0, atol=0.01)


def test_all_negative():
    """All-negative should be valid and produce e-value ≤ 1.0."""
    result = paired_advantage_evalue([-1.0] * 40, theta0=0.0)
    assert result <= 1.0


def test_empty():
    """Empty stream should raise ValueError."""
    with pytest.raises(ValueError, match="empty stream"):
        paired_advantage_evalue([], theta0=0.0)


def test_theta0_nan():
    """theta0=nan should raise ValueError."""
    with pytest.raises(ValueError, match="theta0 must be finite"):
        paired_advantage_evalue([0.0], theta0=float("nan"))


def test_theta0_equals_one():
    """theta0=1.0 should raise ValueError."""
    with pytest.raises(ValueError, match="theta0 must be finite and in"):
        paired_advantage_evalue([0.0], theta0=1.0)


def test_stream_with_nan():
    """Stream with nan should raise ValueError."""
    with pytest.raises(ValueError, match="increments must be finite"):
        paired_advantage_evalue([0.0, float("nan"), 1.0], theta0=0.0)


def test_null_mean_not_exceeding_one_enumeration():
    """Exact null-mean enumeration over {-1,1}^4: sum of e-values over all 16 orderings at boundary null ≤ 1."""
    import itertools
    n, q = 4, 0.5  # boundary null E[W]=0, P(-1)=P(+1)=0.5
    total = sum(
        (q ** c.count(-1.0)) * (q ** c.count(1.0)) * paired_advantage_evalue(list(c), theta0=0.0)
        for c in itertools.product((-1.0, 1.0), repeat=n)
    )
    assert total <= 1.0 + 1e-9
