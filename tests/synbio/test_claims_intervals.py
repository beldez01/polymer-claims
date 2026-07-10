"""Task 4 — C3 (CAR triggering threshold) + C4 (endosomal escape): interval values + range gap."""
import pytest

from polymer_grammar.leaf import MeasurementBasis

from polymer_claims.synbio.claims import car_threshold_claim, endosomal_escape_claim


def test_c3_c4_build_as_derived():
    c3, c4 = car_threshold_claim(), endosomal_escape_claim()
    assert c3.leaves[0].value == 1e3
    assert c4.leaves[0].value == 0.03
    assert c3.leaves[0].measurement_basis is MeasurementBasis.DERIVED
    assert c4.leaves[0].measurement_basis is MeasurementBasis.DERIVED
    # C3 spans 1e2..1e4 — we refuse to fake a symmetric uncertainty bar over two decades.
    assert c3.leaves[0].uncertainty is None


@pytest.mark.xfail(
    reason="grammar gap (general-class): no interval/range leaf; a 1e2..1e4 threshold cannot be "
    "carried by value+symmetric uncertainty; see docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md",
    strict=True,
)
def test_c3_interval_gap():
    # WANT: honest low/high bounds for a two-orders-of-magnitude range.
    leaf = car_threshold_claim().leaves[0]
    assert getattr(leaf, "low", None) is not None and getattr(leaf, "high", None) is not None
