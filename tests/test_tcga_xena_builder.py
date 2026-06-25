# tests/test_tcga_xena_builder.py
import gzip, json
import pytest
from pathlib import Path
from polymer_claims.ingest.tcga_xena import (
    build_real_contract, compute_canonical_checksum, RealBuildResult, STEM,
)
from polymer_claims.contracts import load_contract, using_contract_root, clear_contract_cache

# --- fixture: a tiny Xena-shaped matrix + cBioPortal stubs with a planted DM signal -------------
def _make_fixture(root: Path, *, n_probes=60, n_dm=20):
    cases = [f"TCGA-AB-{2800+i}" for i in range(8)]          # 8 patients
    idh_mut = {cases[0], cases[1], cases[2]}                 # 3 IDH-mut
    aliquots = [f"{c}-03A" for c in cases]                   # one aliquot per case
    xena = root / "matrix.tsv.gz"
    with gzip.open(xena, "wt") as fh:
        fh.write("\t".join(["probe", *aliquots]) + "\n")
        for p in range(n_probes):
            row = [f"cg{p:06d}"]
            for c in cases:
                if p < n_dm:                                 # planted: IDH_mut hyper-methylated
                    v = 0.80 if c in idh_mut else 0.30
                else:
                    v = 0.50
                row.append(f"{v:.4f}")
            fh.write("\t".join(row) + "\n")
    cbio = root / "cbio"; cbio.mkdir()
    (cbio / "data_mutations.txt").write_text(
        "Hugo_Symbol\tTumor_Sample_Barcode\tHGVSp_Short\n"
        + "".join(f"IDH1\t{c}-03A\tp.R132H\n" for c in idh_mut))
    (cbio / "sequenced_samples.json").write_text(json.dumps([f"{c}-03A" for c in cases]))
    return xena, cbio

_KW = dict(idh_call_source="cbioportal:laml_tcga_pub@testcommit",
           idh_count_band=(1, 50), required_idh_mut_controls=frozenset())

def _build(out, xena, cbio, **overrides):
    """Call build_real_contract with explicit cBioPortal file paths + the synthetic-test defaults."""
    return build_real_contract(
        out, xena,
        mutations_file=cbio / "data_mutations.txt",
        sequenced_file=cbio / "sequenced_samples.json",
        **{**_KW, **overrides})

def test_builds_at2_contract_that_loads(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    out = tmp_path / "contracts"
    r = _build(out, xena, cbio)
    assert isinstance(r, RealBuildResult)
    assert r.uid == "tcga_laml_idh@2"
    assert r.idh_mut_n == 3 and r.wt_n == 5 and r.n_probes == 60
    with using_contract_root(out):
        clear_contract_cache()
        ref = load_contract("se:tcga_laml_idh@2")
        assert ref.contract_uid == "tcga_laml_idh@2"
    clear_contract_cache()

def test_ungenotyped_case_dropped_not_defaulted_wt(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    # drop one case from the sequenced list -> it must be dropped from the universe, not called WT
    seq = json.loads((cbio / "sequenced_samples.json").read_text())
    (cbio / "sequenced_samples.json").write_text(json.dumps(seq[:-1]))
    r = _build(tmp_path / "c", xena, cbio)
    assert r.idh_mut_n + r.wt_n == 7          # 8 beta cases - 1 ungenotyped
    assert r.dropped_ungenotyped_n == 1

def test_non_hotspot_variant_is_wt(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    (cbio / "data_mutations.txt").write_text(
        "Hugo_Symbol\tTumor_Sample_Barcode\tHGVSp_Short\n"
        "TP53\tTCGA-AB-2800-03A\tp.R175H\n")     # not an IDH hotspot
    # idh_mut_n will be 0, so the band must allow 0 (override the _KW (1,50) default)
    r = _build(tmp_path / "c", xena, cbio, idh_count_band=(0, 50))
    assert r.idh_mut_n == 0

def test_count_band_violation_aborts(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    with pytest.raises(ValueError, match="outside band"):
        _build(tmp_path / "c", xena, cbio, idh_count_band=(20, 50))

def test_missing_control_aborts(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    with pytest.raises(ValueError, match="controls not called"):
        _build(tmp_path / "c", xena, cbio, required_idh_mut_controls=frozenset({"TCGA-ZZ-9999"}))

def test_builder_is_deterministic(tmp_path):
    xena, cbio = _make_fixture(tmp_path)
    r1 = _build(tmp_path / "a", xena, cbio)
    r2 = _build(tmp_path / "b", xena, cbio)
    b1 = (tmp_path / "a" / f"{STEM}.json").read_bytes() + (tmp_path / "a" / f"{STEM}.betas.tsv").read_bytes()
    b2 = (tmp_path / "b" / f"{STEM}.json").read_bytes() + (tmp_path / "b" / f"{STEM}.betas.tsv").read_bytes()
    assert b1 == b2                                # byte-identical
    assert compute_canonical_checksum(tmp_path / "a") == compute_canonical_checksum(tmp_path / "b")
    assert r1.group_digest == r2.group_digest
