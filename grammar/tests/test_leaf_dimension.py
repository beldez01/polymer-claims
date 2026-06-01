from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.units import Dimension


def test_quantity_without_dimension_still_builds():  # back-compat
    q = QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f")
    assert q.dimension is None


def test_quantity_with_dimension_builds():
    q = QuantityLeaf(value=37.0, unit="Cel", measurement_basis=MeasurementBasis.FUNDAMENTAL,
                     dimension=Dimension.base("temperature"))
    assert q.dimension == Dimension.base("temperature")


def test_quantity_with_dimension_is_hashable():
    q = QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f",
                     dimension=Dimension.base("length") / Dimension.base("time"))
    assert isinstance(hash(q), int)
