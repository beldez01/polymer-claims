from __future__ import annotations

import pytest
from polymer_grammar import DataHandle, MeasurementBasis, OperationNode, ProducedLeafSpec

from polymer_claims import contracts
from polymer_claims.ingest.gdsc_pharmaco import build_pharmaco_contract
from polymer_claims.pharmaco_adapters import PharmacoMeanDiffAdapter, PharmacoRankAdapter


def _node(ref, marker, drug):
    return OperationNode(
        id="n", impl="pharmaco::assoc",
        inputs=(DataHandle(ref=ref),),
        params=(("marker", marker), ("drug", drug), ("group_col", "Sample_Group")),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def _build(tmp_path, betas, aucs, tissue):
    return "se:" + build_pharmaco_contract(betas, aucs, tissue, genes=list(betas),
                                           drugs=list(aucs), out_dir=tmp_path)


def test_within_tissue_split_recovers_signal_a_global_split_would_miss(tmp_path):
    # Two tissues with DISJOINT methylation ranges: skin {0.2..0.5}, lung {0.6..0.9}. A global
    # median (0.55) would split skin-vs-lung (a pure tissue confound) -> ~no signal. The correct
    # within-tissue split ranks high-vs-low meth INSIDE each tissue, where high-meth lines are the
    # sensitive (low-AUC) ones. Per-tissue leg value ~ +0.30; a global split gives ~ +0.02. The
    # >0.2 assertions PASS for the per-tissue split and FAIL for a global one, so a regression to
    # global (non-tissue-adjusted) splitting is caught.
    skin = {"s1": (0.2, 0.90), "s2": (0.3, 0.85), "s3": (0.4, 0.60), "s4": (0.5, 0.55)}
    lung = {"g1": (0.6, 0.88), "g2": (0.7, 0.83), "g3": (0.8, 0.58), "g4": (0.9, 0.53)}
    cells = {**skin, **lung}
    tissue = {**{k: "skin" for k in skin}, **{k: "lung" for k in lung}}
    betas = {"G": {k: m for k, (m, _) in cells.items()}}
    aucs = {"D": {k: a for k, (_, a) in cells.items()}}
    ref = _build(tmp_path, betas, aucs, tissue)
    node = _node(ref, "G", "D")

    contracts.clear_contract_cache()
    with contracts.using_contract_root(tmp_path):
        a = PharmacoMeanDiffAdapter().execute(node, (), None).value
        b = PharmacoRankAdapter().execute(node, (), None).value

    assert a > 0.2   # high-meth lines more sensitive; a global split would give ~0.02 and fail
    assert b > 0.2


def test_missing_drug_row_raises(tmp_path):
    betas = {"G": {"s1": 0.2, "s2": 0.8, "g1": 0.3, "g2": 0.9}}
    aucs = {"D": {"s1": 0.9, "s2": 0.5, "g1": 0.85, "g2": 0.55}}
    tissue = {"s1": "skin", "s2": "skin", "g1": "lung", "g2": "lung"}
    ref = _build(tmp_path, betas, aucs, tissue)
    node = _node(ref, "G", "NOSUCHDRUG")   # feature row auc::NOSUCHDRUG absent

    contracts.clear_contract_cache()
    with contracts.using_contract_root(tmp_path):
        with pytest.raises(KeyError):
            PharmacoMeanDiffAdapter().execute(node, (), None)


def test_wrong_impl_rejected(tmp_path):
    betas = {"G": {"s1": 0.2, "s2": 0.8, "g1": 0.3, "g2": 0.9}}
    aucs = {"D": {"s1": 0.9, "s2": 0.5, "g1": 0.85, "g2": 0.55}}
    tissue = {"s1": "skin", "s2": "skin", "g1": "lung", "g2": "lung"}
    ref = _build(tmp_path, betas, aucs, tissue)
    node = OperationNode(
        id="n", impl="methyl::region_delta_beta",   # not pharmaco::assoc
        inputs=(DataHandle(ref=ref),),
        params=(("marker", "G"), ("drug", "D"), ("group_col", "Sample_Group")),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    contracts.clear_contract_cache()
    with contracts.using_contract_root(tmp_path):
        with pytest.raises(ValueError, match="pharmaco::assoc"):
            PharmacoMeanDiffAdapter().execute(node, (), None)
