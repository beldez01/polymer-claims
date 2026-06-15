from __future__ import annotations

from polymer_claims.evidence import count_enrichment_evalue


def test_empty_is_one():
    assert count_enrichment_evalue([], p0=0.05) == 1.0


def test_no_enrichment_is_one():
    # every probe null (X=0 < p0): GRAPA bets nothing, e == 1.0 exactly
    assert count_enrichment_evalue([0] * 20, p0=0.05) == 1.0


def test_mild_enrichment_above_one():
    e = count_enrichment_evalue([1] * 5 + [0] * 19, p0=0.05)  # 5/24 >> 0.05
    assert e > 1.5


def test_strong_enrichment_clears_bar():
    e = count_enrichment_evalue([1] * 12 + [0] * 12, p0=0.05)  # 12/24, huge enrichment
    assert e > 100.0


def test_monotone_in_count():
    lo = count_enrichment_evalue([1] * 3 + [0] * 21, p0=0.05)
    hi = count_enrichment_evalue([1] * 8 + [0] * 16, p0=0.05)
    assert hi > lo


def test_deterministic():
    seq = [1, 0, 1, 0, 0] * 4
    assert count_enrichment_evalue(seq, p0=0.05) == count_enrichment_evalue(seq, p0=0.05)
