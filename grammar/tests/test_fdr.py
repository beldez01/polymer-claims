import math

import pytest

from polymer_grammar.fdr import _gamma


def test_gamma_first_term():
    assert _gamma(1) == pytest.approx(6 / math.pi**2)


def test_gamma_monotone_decreasing():
    assert _gamma(1) > _gamma(2) > _gamma(3)


def test_gamma_partial_sum_converges_to_one():
    # Σ_{j≥1} (6/π²)/j² = 1 (Basel); first 1000 terms get within 1e-2.
    assert sum(_gamma(j) for j in range(1, 1001)) == pytest.approx(1.0, abs=1e-2)
