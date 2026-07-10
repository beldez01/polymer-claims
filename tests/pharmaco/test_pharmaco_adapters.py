from __future__ import annotations

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


def _contract(tmp_path):
    lines = [f"L{i}" for i in range(8)]
    tissue = {ln: ("skin" if i < 4 else "lung") for i, ln in enumerate(lines)}
    # split within tissue: give each tissue both hi and lo meth so the within-tissue split is
    # real (not just a global tissue confound) -- high-meth (even index) lines are sensitive
    # (low AUC), low-meth (odd index) lines are resistant (high AUC), in BOTH tissues.
    betas = {"CDKN2A": {ln: (0.9 if i % 2 == 0 else 0.1) for i, ln in enumerate(lines)}}
    aucs = {"Palbociclib": {ln: (0.55 if i % 2 == 0 else 0.95) for i, ln in enumerate(lines)}}
    return build_pharmaco_contract(betas, aucs, tissue, genes=["CDKN2A"],
                                    drugs=["Palbociclib"], out_dir=tmp_path)


def test_both_legs_positive_on_planted_sensitivity(tmp_path):
    uid = _contract(tmp_path)
    ref = "se:" + uid
    node = _node(ref, "CDKN2A", "Palbociclib")
    contracts.clear_contract_cache()
    with contracts.using_contract_root(tmp_path):
        a = PharmacoMeanDiffAdapter().execute(node, (), None).value
        b = PharmacoRankAdapter().execute(node, (), None).value
    assert a > 0
    assert b > 0  # high-meth lines are more sensitive
