"""The expression::absence safety e-value — evidence a target sits below a ceiling across tissues."""
from __future__ import annotations

from polymer_claims.expression_absence_evidence import expression_absence_evalue


def test_absent_target_gives_large_evalue():
    # ceiling 20 TPM; a target absent across tissues (~0-1 TPM) -> big headroom -> e >> 1 (safe).
    e = expression_absence_evalue([0.0, 0.2, 0.1, 0.5, 0.0, 0.3] * 5, ceiling=20.0)
    assert e > 5.0


def test_broadly_expressed_target_gives_small_evalue():
    # a target at/above the ceiling in every tissue -> no headroom -> e ~ 1 (safety NOT earned).
    e = expression_absence_evalue([25.0, 30.0, 22.0, 28.0] * 5, ceiling=20.0)
    assert e < 2.0


def test_one_hot_tissue_lowers_the_evalue_vs_all_absent():
    # A single very-high tissue removes headroom there; the e-value should drop vs uniformly-absent.
    # (The HARD veto is the max<=ceiling criterion in the adapter; here we only assert the direction.)
    all_absent = expression_absence_evalue([0.0] * 20, ceiling=20.0)
    one_hot = expression_absence_evalue([0.0] * 19 + [200.0], ceiling=20.0)
    assert one_hot < all_absent


def test_bigger_margin_below_ceiling_is_more_evidence():
    # deeper headroom (further below the ceiling) -> more evidence of safety. Few samples so the
    # betting capital does not saturate at its cap (which would tie both at the ceiling numerically).
    shallow = expression_absence_evalue([17.0] * 5, ceiling=20.0)   # just under (X=0.15)
    deep = expression_absence_evalue([2.0] * 5, ceiling=20.0)       # far under (X=0.90)
    assert deep > shallow


def test_empty_is_zero_not_fabricated():
    assert expression_absence_evalue([], ceiling=20.0) == 0.0


def test_one_hot_unsafe_tissue_gives_zero_evalue():
    # AUDIT finding 1/2: a single tissue above the ceiling REFUTES safety -> the e-value must not
    # support it (else a vetoed target inflates the FDR discovery budget). Worst-tissue gate.
    assert expression_absence_evalue([0.0] * 100 + [3000.0], ceiling=13.0) == 0.0
    # exactly at the ceiling is still safe (<=); just above is not.
    assert expression_absence_evalue([5.0] * 10 + [13.0], ceiling=13.0) > 0.0
    assert expression_absence_evalue([5.0] * 10 + [13.001], ceiling=13.0) == 0.0


def test_null_target_at_ceiling_is_weak_evidence():
    # A target sitting AT the ceiling in every tissue has zero headroom -> e-value ~ 1 (no discovery).
    assert expression_absence_evalue([20.0] * 30, ceiling=20.0) < 2.0
