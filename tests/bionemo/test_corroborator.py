import pytest
from polymer_grammar import MaterializationContext, OperationNode, ProducedLeafSpec, MeasurementBasis
from tests.fixtures.synthetic_corroborator import SyntheticCorroboratorAdapter


def _node(impl="bionemo::plumbing"):
    return OperationNode(
        id="n0", impl=impl,
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def test_corroborator_returns_fixed_value():
    a = SyntheticCorroboratorAdapter(impl="bionemo::plumbing", value=0.12)
    out = a.execute(_node(), (), MaterializationContext(id="M1", api_version="v1", data_version="d1"))
    assert out.value == pytest.approx(0.12)


def test_corroborator_raises_on_unhandled_impl():
    a = SyntheticCorroboratorAdapter(impl="bionemo::plumbing", value=0.12)
    with pytest.raises(ValueError):
        a.execute(_node(impl="other::x"), (), MaterializationContext(id="M1", api_version="v1", data_version="d1"))
