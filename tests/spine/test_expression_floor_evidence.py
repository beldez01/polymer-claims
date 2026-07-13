import pytest


def test_strong_gap_gives_large_evalue():
    from polymer_claims.expression_floor_evidence import _gap_evalue
    # pos ~ CAP-scaled ~0.9, neg ~0 -> a big, consistent gap -> e-value >> 1
    e = _gap_evalue(pos=[90.0, 95.0, 100.0, 92.0, 88.0, 97.0], neg=[0.0, 0.1, 0.05] * 20)
    assert e > 5.0


def test_zero_gap_gives_evalue_near_one():
    from polymer_claims.expression_floor_evidence import _gap_evalue
    # both groups identical (housekeeping-like) -> no discrimination -> e-value ~ 1
    same = [3000.0, 3100.0, 2900.0] * 10
    e = _gap_evalue(pos=same, neg=same)
    assert e < 2.0
