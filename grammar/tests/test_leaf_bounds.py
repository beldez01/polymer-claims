"""GAP-3 — optional low/high bounds on QuantityLeaf (interval/range/one-sided bound).

Load-bearing property is BYTE-IDENTITY: a boundless QuantityLeaf must serialize exactly as it
did before the fields existed (no new key), so every existing corpus is unaffected.
"""
import pytest
from pydantic import ValidationError

from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf

# Captured from the pre-change grammar (the byte-identity baseline — must stay exact).
_FUND_BASELINE = (
    '{"kind":"quantity","value":2.0,"unit":"kcal/mol","uncertainty":1.0,'
    '"measurement_basis":"fundamental","formula":null,"dimension":null}'
)


def test_boundless_leaf_is_byte_identical():
    f = QuantityLeaf(
        value=2.0, unit="kcal/mol", uncertainty=1.0,
        measurement_basis=MeasurementBasis.FUNDAMENTAL,
    )
    assert f.model_dump_json() == _FUND_BASELINE       # no "low"/"high" keys leak
    assert "low" not in f.model_dump() and "high" not in f.model_dump()


def test_floor_bound_builds_and_round_trips():
    # one-sided floor: ">10 weeks" -> low=10, high open, value==low
    leaf = QuantityLeaf(
        value=10.0, unit="weeks", measurement_basis=MeasurementBasis.FUNDAMENTAL, low=10.0,
    )
    dumped = leaf.model_dump_json()
    assert '"low":10.0' in dumped and '"high"' not in dumped
    back = QuantityLeaf.model_validate_json(dumped)
    assert back.low == 10.0 and back.high is None


def test_ceiling_bound_builds():
    leaf = QuantityLeaf(
        value=2000.0, unit="molecules/cell", measurement_basis=MeasurementBasis.FUNDAMENTAL, high=2000.0,
    )
    assert leaf.high == 2000.0 and leaf.low is None


def test_closed_range_builds():
    leaf = QuantityLeaf(
        value=10.0, measurement_basis=MeasurementBasis.DERIVED, formula="dynamic_range",
        low=10.0, high=100.0,
    )
    assert leaf.low == 10.0 and leaf.high == 100.0


def test_ordering_rejected_when_low_not_less_than_high():
    with pytest.raises(ValidationError, match="low < high"):
        QuantityLeaf(value=5.0, measurement_basis=MeasurementBasis.DERIVED, formula="f",
                     low=5.0, high=5.0)


def test_containment_rejected_value_below_low():
    with pytest.raises(ValidationError, match="below low bound"):
        QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f",
                     low=10.0, high=100.0)


def test_containment_rejected_value_above_high():
    with pytest.raises(ValidationError, match="above high bound"):
        QuantityLeaf(value=200.0, measurement_basis=MeasurementBasis.DERIVED, formula="f",
                     low=10.0, high=100.0)


def test_spread_exclusivity_bound_plus_uncertainty_rejected():
    with pytest.raises(ValidationError, match="two spread encodings"):
        QuantityLeaf(value=10.0, uncertainty=1.0, measurement_basis=MeasurementBasis.DERIVED,
                     formula="f", low=10.0, high=100.0)
