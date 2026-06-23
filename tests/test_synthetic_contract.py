import json

from polymer_claims.contracts import clear_contract_cache, load_contract, using_contract_root
from polymer_claims.ingest.synthetic import build_synthetic_contract, N_PROBES, N_SAMPLES


def test_generator_is_deterministic(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"
    build_synthetic_contract(a); build_synthetic_contract(b)
    ta = (a / "tcga_laml_idh_synth.betas.tsv").read_bytes()
    tb = (b / "tcga_laml_idh_synth.betas.tsv").read_bytes()
    assert ta == tb and len(ta) > 0          # same seed -> identical betas TSV bytes


def test_contract_resolves_through_the_real_loader(tmp_path):
    # Exercise the actual load_contract path (not just the manifest JSON), scoped to tmp_path.
    uid = build_synthetic_contract(tmp_path)
    assert uid == "tcga_laml_idh_synth@1"
    with using_contract_root(tmp_path):
        clear_contract_cache()
        se = load_contract("se:tcga_laml_idh_synth@1")
    assert se.contract_uid == "tcga_laml_idh_synth@1"


def test_manifest_has_expected_shape(tmp_path):
    build_synthetic_contract(tmp_path)
    manifest = json.loads((tmp_path / "tcga_laml_idh_synth.json").read_text())
    assert manifest["dim"] == [N_PROBES, N_SAMPLES]     # all autosomal probes survive QC
    assert {c["Sample_Group"] for c in manifest["col_data"]} == {"WT", "IDH_mut"}
    assert all(not r["chr"].endswith(("X", "Y")) for r in manifest["row_data"])  # autosomal only
