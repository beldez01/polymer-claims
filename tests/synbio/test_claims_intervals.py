"""Task 4 — C3 (CAR triggering threshold) + C4 (endosomal escape): interval values + range gap."""
import pytest

from polymer_grammar.leaf import MeasurementBasis

from polymer_claims.synbio.claims import car_threshold_claim, endosomal_escape_claim


def test_c3_c4_build_as_derived():
    c3, c4 = car_threshold_claim(), endosomal_escape_claim()
    assert c3.leaves[0].value == 1e3
    assert c3.leaves[0].low == 1e2 and c3.leaves[0].high == 1e4   # NEW honest bounds
    assert c4.leaves[0].value == 0.03
    assert c3.leaves[0].measurement_basis is MeasurementBasis.DERIVED
    assert c4.leaves[0].measurement_basis is MeasurementBasis.DERIVED
    # C3 spans 1e2..1e4 — we refuse to fake a symmetric uncertainty bar over two decades.
    assert c3.leaves[0].uncertainty is None


def test_c3_interval_gap():
    # WANT: honest low/high bounds for a two-orders-of-magnitude range. Tripwire flips when
    # C3 is re-expressed with explicit bounds (the candidate-(a) IntervalLeaf resolution, GAP-3).
    leaf = car_threshold_claim().leaves[0]
    assert getattr(leaf, "low", None) is not None and getattr(leaf, "high", None) is not None


@pytest.mark.xfail(reason="GAP-9 deferred: no log/geometric-scale marker on QuantityLeaf (YAGNI, "
                          "no consumer computes inside the interval yet)", strict=True)
def test_gap9_logscale_marker_deferred():
    from polymer_grammar.leaf import QuantityLeaf
    leaf = QuantityLeaf(value=10.0, measurement_basis=MeasurementBasis.DERIVED, formula="f",
                        low=10.0, high=100.0)
    assert getattr(leaf, "scale", None) == "log"


@pytest.mark.xfail(reason="GAP-10 deferred: no discrete-integer marker on QuantityLeaf (YAGNI, no "
                          "consumer interpolates inside the interval yet)", strict=True)
def test_gap10_discrete_marker_deferred():
    from polymer_grammar.leaf import QuantityLeaf
    leaf = QuantityLeaf(value=3.0, unit="layers", measurement_basis=MeasurementBasis.FUNDAMENTAL,
                        low=3.0, high=4.0)
    assert getattr(leaf, "discrete", None) is True
