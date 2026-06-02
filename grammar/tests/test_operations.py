import pytest
from pydantic import ValidationError

from polymer_grammar.leaf import MeasurementBasis
from polymer_grammar.operations import (
    DataHandle,
    NodeRef,
    OperationNode,
    ProducedLeafSpec,
)
from polymer_grammar.units import Dimension


def _produces_quantity(**kw):
    base = dict(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED)
    base.update(kw)
    return ProducedLeafSpec(**base)


def test_data_handle_requires_nonempty_ref():
    h = DataHandle(ref="tcga:methylation:cg12345")
    assert h.kind == "data_handle"
    with pytest.raises(ValidationError):
        DataHandle(ref="")


def test_node_ref_carries_target():
    r = NodeRef(node_id="n1")
    assert r.kind == "node_ref"
    assert r.node_id == "n1"


def test_produced_spec_unit_only_for_fundamental_quantity():
    ProducedLeafSpec(
        leaf_kind="quantity", measurement_basis=MeasurementBasis.FUNDAMENTAL, unit="m"
    )
    with pytest.raises(ValidationError):
        ProducedLeafSpec(
            leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED, unit="m"
        )


def test_produced_spec_nonquantity_forbids_unit_and_basis():
    ProducedLeafSpec(leaf_kind="categorical")
    with pytest.raises(ValidationError):
        ProducedLeafSpec(leaf_kind="categorical", unit="m")
    with pytest.raises(ValidationError):
        ProducedLeafSpec(leaf_kind="existence", measurement_basis=MeasurementBasis.DERIVED)


def test_operation_node_builds_with_mixed_inputs():
    node = OperationNode(
        id="corr",
        impl="python::scipy.stats.spearmanr",
        inputs=(DataHandle(ref="layer:col_x"), NodeRef(node_id="prep")),
        params=(("axis", "0"),),
        produces=_produces_quantity(dimension=Dimension(exponents=())),
    )
    assert node.id == "corr"
    assert node.inputs[0].kind == "data_handle"
    assert node.inputs[1].kind == "node_ref"
    assert node.oracle_ref is None


def test_operation_node_is_hashable():
    node = OperationNode(id="n", impl="builtin::const", produces=_produces_quantity())
    assert isinstance(hash(node), int)
