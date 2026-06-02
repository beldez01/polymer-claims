from polymer_grammar.evaluate import (
    ExecValue,
    IdentityAdapter,
    ReferenceAdapter,
    SelfLicensingError,
)
from polymer_grammar.leaf import MeasurementBasis
from polymer_grammar.licensing import MaterializationContext
from polymer_grammar.operations import OperationNode, ProducedLeafSpec


def _ctx():
    return MaterializationContext(
        id="m1", api_version="0.9.x", data_version="db@2026-06-02"
    )


def _q():
    return ProducedLeafSpec(
        leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED
    )


def test_exec_value_holds_scalar():
    assert ExecValue(value=1.5).value == 1.5
    assert ExecValue(value=None).value is None


def test_self_licensing_error_exists():
    assert issubclass(SelfLicensingError, Exception)
    err = SelfLicensingError("writer must not be the verifier")
    assert "verifier" in str(err)


def test_const_impl_agrees_across_two_implementations():
    node = OperationNode(
        id="a", impl="builtin::const", params=(("value", "0.03"),), produces=_q()
    )
    a = IdentityAdapter()
    b = ReferenceAdapter()
    assert a.identity != b.identity
    va = a.execute(node, (), _ctx())
    vb = b.execute(node, (), _ctx())
    assert va.value == vb.value == 0.03


def test_mean_impl_computed_independently_agrees():
    node = OperationNode(
        id="a", impl="builtin::mean", params=(("vector", "1,2,3,4"),), produces=_q()
    )
    va = IdentityAdapter().execute(node, (), _ctx())
    vb = ReferenceAdapter().execute(node, (), _ctx())
    assert va.value == vb.value == 2.5


def test_perturbed_reference_adapter_disagrees():
    node = OperationNode(
        id="a", impl="builtin::const", params=(("value", "0.03"),), produces=_q()
    )
    vb = ReferenceAdapter(perturb=1.0).execute(node, (), _ctx())
    assert vb.value == 1.03


def test_identity_impl_passes_through_upstream_with_dimension():
    from polymer_grammar.units import Dimension

    node = OperationNode(id="a", impl="builtin::identity", produces=_q())
    up = (ExecValue(value=2.0, dimension=Dimension.base("length")),)
    va = IdentityAdapter().execute(node, up, _ctx())
    vb = ReferenceAdapter().execute(node, up, _ctx())
    assert va.value == vb.value == 2.0
    assert va.dimension == vb.dimension == Dimension.base("length")


def test_identity_impl_falls_back_to_param_when_no_upstream():
    node = OperationNode(
        id="a", impl="builtin::identity", params=(("value", "0.5"),), produces=_q()
    )
    va = IdentityAdapter().execute(node, (), _ctx())
    vb = ReferenceAdapter().execute(node, (), _ctx())
    assert va.value == vb.value == 0.5
