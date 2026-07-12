from pathlib import Path

from polymer_claims import contracts as _c
from polymer_claims.ingest.tcga_laml_fusion_expr import build_fusion_expr_contract

_FIX = Path(__file__).parent / "fixtures" / "fusion_expr_mini"
_GENES = ["RUNX1T1", "RUNX1", "ACTB", "GAPDH"]


def _load_fixture():
    rows = [ln.split("\t") for ln in (_FIX / "panel_tpm.tsv").read_text().splitlines()]
    header, data = rows[0], rows[1:]
    cases = header[1:]
    tpm = {r[0]: {c: float(v) for c, v in zip(cases, r[1:])} for r in data}
    lab = [ln.split("\t") for ln in (_FIX / "fusion_labels.tsv").read_text().splitlines()][1:]
    fusion = {r[0]: r[1] for r in lab}
    karyo = {r[0]: r[2] for r in lab}
    return tpm, fusion, karyo


def test_builds_loadable_contract_with_fusion_group(tmp_path):
    tpm, fusion, karyo = _load_fixture()
    uid = build_fusion_expr_contract(tpm, fusion, karyo, genes=_GENES, out_dir=tmp_path)
    assert uid == "tcga_laml_fusion_expr@1"
    _c.clear_contract_cache()
    with _c.using_contract_root(tmp_path):
        ref = _c.load_contract("se:tcga_laml_fusion_expr@1")
        manifest = _c.load_manifest(ref)
    feats = {r["feature_id"] for r in manifest["row_data"]}
    assert feats == {f"expr::{g}" for g in _GENES}
    groups = {c["Sample_Group"] for c in manifest["col_data"]}
    assert groups == {"fusion_pos", "fusion_neg"}
    assert manifest["metadata"]["genome_assembly"] == "hg38"


def test_matrix_values_and_sample_order_are_deterministic(tmp_path):
    tpm, fusion, karyo = _load_fixture()
    build_fusion_expr_contract(tpm, fusion, karyo, genes=_GENES, out_dir=tmp_path)
    tsv = (tmp_path / "tcga_laml_fusion_expr.betas.tsv").read_text()
    lines = tsv.splitlines()
    assert lines[0].split("\t")[0] == "feature_id"
    assert lines[0].split("\t")[1:] == sorted(fusion)          # samples sorted, deterministic
    runx1t1 = next(l for l in lines if l.startswith("expr::RUNX1T1")).split("\t")[1:]
    col = lines[0].split("\t")[1:]
    val = dict(zip(col, runx1t1))
    assert float(val["TCGA-AB-2819"]) > 100 and float(val["TCGA-AB-2802"]) < 1  # signal preserved
