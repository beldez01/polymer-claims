"""test_analytic_basis.py — GAP-7: a third MeasurementBasis for analytic constants.

An information-theoretic / mathematical constant (e.g. 2 bits = log2(4)) is neither instrument-measured
(FUNDAMENTAL) nor a data ratio (DERIVED). ANALYTIC carries its generating `formula` and MAY carry a
definitional `unit` (unlike DERIVED). Existing FUNDAMENTAL/DERIVED discipline is unchanged.
"""
from __future__ import annotations

import pytest

from polymer_grammar import MeasurementBasis, QuantityLeaf


def test_analytic_constant_carries_formula_and_optional_unit():
    leaf = QuantityLeaf(
        value=2.0, measurement_basis=MeasurementBasis.ANALYTIC, formula="log2(4)", unit="bits",
    )
    assert leaf.measurement_basis is MeasurementBasis.ANALYTIC
    assert leaf.formula == "log2(4)" and leaf.unit == "bits"


def test_analytic_without_formula_is_rejected():
    # a bare number claiming to be analytic, with no generating expression, is not honest.
    with pytest.raises(ValueError, match="ANALYTIC quantity must carry its generating"):
        QuantityLeaf(value=2.0, measurement_basis=MeasurementBasis.ANALYTIC)


def test_analytic_allows_a_unit_that_derived_forbids():
    # ANALYTIC may carry a definitional unit ("bits") ...
    QuantityLeaf(value=2.0, measurement_basis=MeasurementBasis.ANALYTIC, formula="log2(4)", unit="bits")
    # ... whereas DERIVED with a unit is still rejected (a data ratio's unit is not meaningful).
    with pytest.raises(ValueError, match="unit is only meaningful for FUNDAMENTAL"):
        QuantityLeaf(value=1.5, measurement_basis=MeasurementBasis.DERIVED, formula="a/b", unit="x")


def test_existing_bases_discipline_unchanged():
    # FUNDAMENTAL: unit meaningful, no formula required.
    QuantityLeaf(value=2.0, measurement_basis=MeasurementBasis.FUNDAMENTAL, unit="kcal/mol")
    # DERIVED: formula required, no unit.
    QuantityLeaf(value=277.0, measurement_basis=MeasurementBasis.DERIVED, formula="edited/unedited")
    with pytest.raises(ValueError, match="DERIVED quantity must carry its generating"):
        QuantityLeaf(value=277.0, measurement_basis=MeasurementBasis.DERIVED)
