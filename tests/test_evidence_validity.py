# tests/test_evidence_validity.py
from __future__ import annotations

import random

from polymer_grammar import Comparator

from polymer_claims.evidence import betting_evalue


def test_evalue_nonneg_and_finite():
    e = betting_evalue([0.1, 0.2, 0.15], [0.9, 0.8, 0.85], threshold=0.10, comparator=Comparator.GT)
    assert 0.0 <= e < float("inf")


def test_evalue_finite_at_zero_variance():
    e_signal = betting_evalue([0.45] * 8, [0.69] * 8, threshold=0.10, comparator=Comparator.GT)
    assert 1.0 < e_signal < float("inf")
    e_null = betting_evalue([0.50] * 8, [0.50] * 8, threshold=0.10, comparator=Comparator.GT)
    assert e_null == 1.0


def test_evalue_validity_under_boundary_null_mean_e_le_one():
    theta0 = 0.10
    for lo_b, hi_b in ((0.18, 0.22), (0.05, 0.35), (-0.10, 0.50)):
        rng = random.Random(7)
        total, trials = 0.0, 3000
        for _ in range(trials):
            a = [min(1.0, max(0.0, rng.uniform(0.0, 0.4))) for _ in range(12)]
            b = [min(1.0, max(0.0, 0.10 + rng.uniform(lo_b, hi_b))) for _ in range(12)]
            total += betting_evalue(a, b, threshold=theta0, comparator=Comparator.GT)
        assert total / trials <= 1.0 + 0.06, f"E[e]={total/trials} > 1 (spread {lo_b},{hi_b})"


def test_evalue_validity_bernoulli_null():
    rng = random.Random(11)
    theta0 = 0.10
    total, trials = 0.0, 3000
    for _ in range(trials):
        a = [1.0 if rng.random() < 0.20 else 0.0 for _ in range(20)]
        b = [1.0 if rng.random() < 0.30 else 0.0 for _ in range(20)]
        total += betting_evalue(a, b, threshold=theta0, comparator=Comparator.GT)
    assert total / trials <= 1.0 + 0.06


def test_evalue_grows_with_margin_and_n():
    small = betting_evalue([0.45] * 12, [0.70] * 12, threshold=0.10, comparator=Comparator.GT)
    big = betting_evalue([0.45] * 40, [0.75] * 40, threshold=0.10, comparator=Comparator.GT)
    assert big > small > 1.0


def test_evalue_lt_mirror_and_degenerate_comparators():
    from polymer_grammar import Comparator
    # LT/LE is the mirror of GT/GE on swapped groups + negated threshold (exact equality).
    a = [0.45, 0.46, 0.44, 0.45]
    b = [0.15, 0.16, 0.14, 0.15]  # b << a: strong evidence that mu_b - mu_a < 0.10
    lt = betting_evalue(a, b, threshold=0.10, comparator=Comparator.LT)
    gt = betting_evalue(b, a, threshold=-0.10, comparator=Comparator.GT)
    assert lt == gt and lt > 1.0
    # non-one-sided comparators and empty input -> 0.0 (no test)
    assert betting_evalue(a, b, threshold=0.10, comparator=Comparator.EQ) == 0.0
    assert betting_evalue([], b, threshold=0.10, comparator=Comparator.GT) == 0.0


def test_evalue_is_deterministic():
    from polymer_grammar import Comparator
    a, b = [0.45] * 10, [0.70] * 10
    e1 = betting_evalue(a, b, threshold=0.10, comparator=Comparator.GT)
    e2 = betting_evalue(a, b, threshold=0.10, comparator=Comparator.GT)
    assert e1 == e2
