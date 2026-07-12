from __future__ import annotations

import pytest
from polymer_grammar import DataHandle, MeasurementBasis, OperationNode, ProducedLeafSpec

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract


def _mini_contract(tmp_path):
    tpm = {"RUNX1T1": {"p1": 90.0, "p2": 100.0, "n1": 0.0, "n2": 0.1, "n3": 0.2}}
    fusion = {"p1": "fusion_pos", "p2": "fusion_pos", "n1": "fusion_neg", "n2": "fusion_neg", "n3": "fusion_neg"}
    karyo = {k: "" for k in fusion}
    build_fusion_expr_contract(tpm, fusion, karyo, genes=["RUNX1T1"], out_dir=tmp_path)
    _c.clear_contract_cache()
    return "se:tcga_laml_fusion_expr@1"


def _node(ref, gene, level_a="fusion_pos", level_b="fusion_neg"):
    return OperationNode(
        id="n", impl="expression::floor",
        inputs=(DataHandle(ref=ref),),
        params=(("gene", gene), ("group_col", "Sample_Group"),
                ("level_a", level_a), ("level_b", level_b)),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def test_split_returns_pos_and_neg(tmp_path):
    from polymer_claims.expression_floor_adapters import _expr_split
    ref = _mini_contract(tmp_path)
    with _c.using_contract_root(tmp_path):
        node = _node(ref, "RUNX1T1")
        pos, neg = _expr_split(node)
    assert sorted(pos) == [90.0, 100.0]
    assert sorted(neg) == [0.0, 0.1, 0.2]


def test_mean_leg_returns_fusion_pos_mean(tmp_path):
    from polymer_claims.expression_floor_adapters import ExpressionFloorMeanAdapter
    ref = _mini_contract(tmp_path)
    with _c.using_contract_root(tmp_path):
        node = _node(ref, "RUNX1T1")
        v = ExpressionFloorMeanAdapter().execute(node, (), None)
    assert v.value == pytest.approx(95.0)   # mean(90,100)


def test_hl_leg_returns_a_pseudo_median_of_fusion_pos(tmp_path):
    from polymer_claims.expression_floor_adapters import ExpressionFloorHLAdapter
    ref = _mini_contract(tmp_path)
    with _c.using_contract_root(tmp_path):
        node = _node(ref, "RUNX1T1")
        v = ExpressionFloorHLAdapter().execute(node, (), None)
    # Walsh averages of {90,100}: 90, 95, 100 -> median = 95
    assert v.value == pytest.approx(95.0)


def test_wrong_impl_rejected(tmp_path):
    from polymer_claims.expression_floor_adapters import ExpressionFloorMeanAdapter
    ref = _mini_contract(tmp_path)
    node = OperationNode(
        id="n", impl="pharmaco::assoc",
        inputs=(DataHandle(ref=ref),),
        params=(("gene", "RUNX1T1"), ("group_col", "Sample_Group"),
                ("level_a", "fusion_pos"), ("level_b", "fusion_neg")),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    with _c.using_contract_root(tmp_path):
        with pytest.raises(ValueError, match="expression::floor"):
            ExpressionFloorMeanAdapter().execute(node, (), None)


def test_missing_gene_row_raises(tmp_path):
    from polymer_claims.expression_floor_adapters import ExpressionFloorMeanAdapter
    ref = _mini_contract(tmp_path)
    node = _node(ref, "NOSUCHGENE")
    with _c.using_contract_root(tmp_path):
        with pytest.raises(KeyError):
            ExpressionFloorMeanAdapter().execute(node, (), None)


def test_two_legs_have_distinct_owners():
    from polymer_claims.expression_floor_adapters import expression_floor_registry
    reg = expression_floor_registry()
    owners = {c.owner for c in reg.credentials}
    assert len(owners) == 2 and len(reg.credentials) == 2
