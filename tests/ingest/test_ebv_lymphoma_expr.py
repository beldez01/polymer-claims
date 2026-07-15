"""EBV+/- lymphoma viral-expression ingest builder (Ch1b) — machinery on a synthetic matrix.

Data-gated (the real matrix needs composite-reference re-quantification, DATA-PLAN §2.1); this checks
the builder packages a viral matrix into a contract the Ch1b feature claim can score.
"""
from __future__ import annotations

from polymer_claims import contracts as _c
from polymer_claims.ingest.ebv_lymphoma_expr import build_ebv_lymphoma_contract


def test_builder_packages_viral_matrix_with_composite_reference(tmp_path):
    tpm = {"LMP1": {"p1": 90.0, "p2": 100.0, "n1": 0.0, "n2": 0.1},
           "EBNA1": {"p1": 40.0, "p2": 55.0, "n1": 0.2, "n2": 0.0}}
    ebv = {"p1": "EBV_pos", "p2": "EBV_pos", "n1": "EBV_neg", "n2": "EBV_neg"}
    build_ebv_lymphoma_contract(tpm, ebv, features=["LMP1", "EBNA1"], out_dir=tmp_path)
    with _c.using_contract_root(tmp_path):
        se = _c.load_contract("se:ebv_lymphoma_expr@1")
        m = _c.load_manifest(se)
    # composite reference recorded (not bare hg38); groups match the Ch1b claim's level_a/level_b.
    assert m["metadata"]["genome_assembly"] == "GRCh38+EBV(NC_007605)"
    assert {c["Sample_Group"] for c in m["col_data"]} == {"EBV_pos", "EBV_neg"}
    assert [r["feature_id"] for r in m["row_data"]] == ["expr::EBNA1", "expr::LMP1"]
