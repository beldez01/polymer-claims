from __future__ import annotations

from polymer_grammar import Comparator, DataHandle, MeasurementBasis, OperationNode, ProducedLeafSpec

from polymer_claims import contracts
from polymer_claims.ingest.gdsc_pharmaco import build_pharmaco_contract
from polymer_claims.pharmaco_evidence import pharmaco_evalue


def _node(ref):
    return OperationNode(
        id="n", impl="pharmaco::assoc",
        inputs=(DataHandle(ref=ref),),
        params=(("marker", "G"), ("drug", "D"), ("group_col", "Sample_Group")),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def test_evalue_high_on_signal_low_on_null(tmp_path):
    lines = [f"L{i}" for i in range(40)]
    # planted signal: even lines low-meth/resistant, odd lines high-meth/sensitive, both tissues
    betas = {"G": {ln: (0.1 if i % 2 == 0 else 0.9) for i, ln in enumerate(lines)}}
    aucs_sig = {"D": {ln: (0.9 if i % 2 == 0 else 0.4) for i, ln in enumerate(lines)}}
    aucs_null = {"D": {ln: 0.7 for ln in lines}}
    tissue = {ln: ("a" if i < 20 else "b") for i, ln in enumerate(lines)}

    contracts.clear_contract_cache()
    with contracts.using_contract_root(tmp_path):
        ref_sig = "se:" + build_pharmaco_contract(
            betas, aucs_sig, tissue, genes=["G"], drugs=["D"], out_dir=tmp_path
        )
        contracts.clear_contract_cache()
        e_sig = pharmaco_evalue(_node(ref_sig), threshold=0.0, comparator=Comparator.GT)

        ref_null = "se:" + build_pharmaco_contract(
            betas, aucs_null, tissue, genes=["G"], drugs=["D"], out_dir=tmp_path,
            uid_stem="gdsc_pharmaco",  # overwrite
        )
        contracts.clear_contract_cache()
        e_null = pharmaco_evalue(_node(ref_null), threshold=0.0, comparator=Comparator.GT)

    assert e_sig > 2.0        # accrues capital against the null
    assert e_null < 1.5       # no license-worthy evidence
