import pytest
from polymer_grammar import DataHandle, MaterializationContext, OperationNode, ProducedLeafSpec
from polymer_grammar import MeasurementBasis
from polymer_claims.bionemo.adapters import BioNeMoNIMAdapter
from polymer_claims.bionemo.client import NimClient, NimRequest, NimResponse


def _client(tmp_path, value):
    def transport(req: NimRequest, api_key: str) -> NimResponse:
        return NimResponse(status=200, body={"out": {"score": value}, "model": "m1"}, model_version=None)
    return NimClient(transport=transport, cache_dir=tmp_path, api_key="k")


def _node(impl="bionemo::plumbing"):
    return OperationNode(
        id="n0", impl=impl, inputs=(DataHandle(ref="seq1"),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def _ctx():
    return MaterializationContext(id="M1", api_version="v1", data_version="d1")


def test_adapter_maps_nim_response_to_execvalue(tmp_path):
    adapter = BioNeMoNIMAdapter(
        _client(tmp_path, 0.12), impl="bionemo::plumbing", endpoint="https://x/fold",
        value_path=("out", "score"), substrate={"seq1": {"sequence": "MAAA"}},
    )
    out = adapter.execute(_node(), (), _ctx())
    assert out.value == pytest.approx(0.12)


def test_adapter_raises_on_unhandled_impl(tmp_path):
    adapter = BioNeMoNIMAdapter(
        _client(tmp_path, 0.12), impl="bionemo::plumbing", endpoint="https://x/fold",
        value_path=("out", "score"), substrate={"seq1": {"sequence": "MAAA"}},
    )
    with pytest.raises(ValueError, match="cannot execute impl"):
        adapter.execute(_node(impl="stats::mean_diff"), (), _ctx())


def test_adapter_raises_when_node_has_no_data_handle(tmp_path):
    """A node with no DataHandle input must raise ValueError."""
    node_no_handle = OperationNode(
        id="n0",
        impl="bionemo::plumbing",
        inputs=(),  # no inputs at all — no DataHandle
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    adapter = BioNeMoNIMAdapter(
        _client(tmp_path, 0.12), impl="bionemo::plumbing", endpoint="https://x/fold",
        value_path=("out", "score"), substrate={"seq1": {"sequence": "MAAA"}},
    )
    with pytest.raises(ValueError, match="no DataHandle input"):
        adapter.execute(node_no_handle, (), _ctx())


def test_adapter_raises_when_substrate_missing_ref(tmp_path):
    """A substrate that doesn't contain the DataHandle's ref must raise ValueError."""
    adapter = BioNeMoNIMAdapter(
        _client(tmp_path, 0.12), impl="bionemo::plumbing", endpoint="https://x/fold",
        value_path=("out", "score"),
        substrate={},  # empty — ref "seq1" is absent
    )
    with pytest.raises(ValueError, match="substrate missing ref"):
        adapter.execute(_node(), (), _ctx())
