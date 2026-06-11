from __future__ import annotations

import json
import re
from pathlib import Path

_DIR = Path(__file__).resolve().parents[1] / "src" / "polymer_claims" / "contracts"
_MANIFEST = _DIR / "tet2_epicv2_demo.json"
_BETAS = _DIR / "tet2_epicv2_demo.betas.tsv"


def _manifest() -> dict:
    return json.loads(_MANIFEST.read_text())


def test_fixture_files_exist():
    assert _MANIFEST.is_file()
    assert _BETAS.is_file()


def test_manifest_dims_match_row_and_col_data():
    m = _manifest()
    n_features, n_samples = m["dim"]
    assert n_features == len(m["row_data"])
    assert n_samples == len(m["col_data"])


def test_betas_matrix_shape_matches_dim():
    m = _manifest()
    n_features, n_samples = m["dim"]
    lines = _BETAS.read_text().splitlines()
    header = lines[0].split("\t")
    assert header[0] == "feature_id"
    assert len(header) == 1 + n_samples
    assert len(lines) - 1 == n_features  # one data row per probe


def test_probe_ids_are_cg_format_and_match_matrix_order():
    m = _manifest()
    cg = re.compile(r"^cg\d{8}$")
    manifest_ids = [r["feature_id"] for r in m["row_data"]]
    assert all(cg.match(fid) for fid in manifest_ids)
    matrix_ids = [ln.split("\t")[0] for ln in _BETAS.read_text().splitlines()[1:]]
    assert manifest_ids == matrix_ids  # same order — the dimnames_hash binds this order


def test_sample_groups_are_binary_and_balanced():
    m = _manifest()
    groups = [c["Sample_Group"] for c in m["col_data"]]
    assert set(groups) == {"TET2_mut", "WT"}
    assert groups.count("TET2_mut") == groups.count("WT")


def test_metadata_is_epicv2_hg38():
    m = _manifest()
    assert m["metadata"]["genome_assembly"] == "hg38"
    assert m["metadata"]["array"] == "EPICv2"
