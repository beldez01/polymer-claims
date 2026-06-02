import pytest
from pydantic import ValidationError

from polymer_grammar.leaf import MeasurementBasis
from polymer_grammar.operations import (
    ComputeGraph,
    DataHandle,
    NodeRef,
    OperationNode,
    ProducedLeafSpec,
)
from polymer_grammar.units import Dimension

_EXPECTED_GRAPH_HASH = "8c75353623d4c5b7ceb0d036a7113789c49b06d41b431c389df24c9dc63bb16c"


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


def _node(id_, impl="builtin::const", inputs=()):
    return OperationNode(
        id=id_, impl=impl, inputs=inputs, produces=_produces_quantity()
    )


def test_graph_builds_and_orders_topologically():
    g = ComputeGraph(
        nodes=(
            _node("a"),
            _node("b", inputs=(NodeRef(node_id="a"),)),
            _node("c", inputs=(NodeRef(node_id="b"),)),
        ),
        terminal="c",
    )
    assert g.topological_order == ("a", "b", "c")


def test_graph_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        ComputeGraph(nodes=(_node("a"), _node("a")), terminal="a")


def test_graph_rejects_dangling_noderef():
    with pytest.raises(ValidationError):
        ComputeGraph(
            nodes=(_node("a", inputs=(NodeRef(node_id="ghost"),)),), terminal="a"
        )


def test_graph_rejects_unknown_terminal():
    with pytest.raises(ValidationError):
        ComputeGraph(nodes=(_node("a"),), terminal="nope")


def test_graph_rejects_cycle():
    with pytest.raises(ValidationError):
        ComputeGraph(
            nodes=(
                _node("a", inputs=(NodeRef(node_id="b"),)),
                _node("b", inputs=(NodeRef(node_id="a"),)),
            ),
            terminal="a",
        )


def test_graph_requires_at_least_one_node():
    with pytest.raises(ValidationError):
        ComputeGraph(nodes=(), terminal="x")


def test_content_hash_is_stable_and_node_order_insensitive():
    a = OperationNode(
        id="a",
        impl="builtin::mean",
        inputs=(DataHandle(ref="layer:x", expected_dimension=Dimension.base("length")),),
        params=(("k", "v"),),
        oracle_ref="oracle:1",
        produces=_produces_quantity(),
    )
    b = OperationNode(
        id="b", impl="builtin::const", inputs=(NodeRef(node_id="a"),),
        produces=_produces_quantity(),
    )
    g1 = ComputeGraph(nodes=(a, b), terminal="b")
    g2 = ComputeGraph(nodes=(b, a), terminal="b")
    assert g1.content_hash == g2.content_hash  # node-declaration-order insensitive
    # Pin the value so accidental serialization drift is caught:
    assert g1.content_hash == _EXPECTED_GRAPH_HASH


def test_topological_order_diamond_breaks_ties_by_declaration_order():
    g = ComputeGraph(
        nodes=(
            _node("a"),
            _node("b", inputs=(NodeRef(node_id="a"),)),
            _node("c", inputs=(NodeRef(node_id="a"),)),
            _node("d", inputs=(NodeRef(node_id="b"), NodeRef(node_id="c"))),
        ),
        terminal="d",
    )
    assert g.topological_order == ("a", "b", "c", "d")
