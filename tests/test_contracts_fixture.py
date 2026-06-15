from __future__ import annotations

import json
import re
from pathlib import Path

_DIR = Path(__file__).resolve().parents[1] / "src" / "polymer_claims" / "contracts"
_MANIFEST = _DIR / "groupdiff_epicv2_demo.json"
_BETAS = _DIR / "groupdiff_epicv2_demo.betas.tsv"


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
    assert set(groups) == {"case", "control"}
    assert groups.count("case") == groups.count("control")


def test_metadata_is_epicv2_hg38():
    m = _manifest()
    assert m["metadata"]["genome_assembly"] == "hg38"
    assert m["metadata"]["array"] == "EPICv2"


def test_betas_columns_match_col_data_sample_order():
    m = _manifest()
    sample_ids = [c["sample_id"] for c in m["col_data"]]
    header = _BETAS.read_text().splitlines()[0].split("\t")
    assert header[1:] == sample_ids  # column order binds sample metadata positionally


def test_planted_shift_present_on_first_five_probes_only():
    m = _manifest()
    groups = {c["sample_id"]: c["Sample_Group"] for c in m["col_data"]}
    lines = _BETAS.read_text().splitlines()
    header = lines[0].split("\t")[1:]
    rows = {ln.split("\t")[0]: ln.split("\t")[1:] for ln in lines[1:]}

    def _by_group(feature_id):
        vals = {"case": [], "control": []}
        for sid, cell in zip(header, rows[feature_id]):
            vals[groups[sid]].append(float(cell))
        return vals

    # probes 0-4 (cg00000001..cg00000005): case exceeds control by ~0.20
    for k in range(1, 6):
        v = _by_group(f"cg{k:08d}")
        assert round(min(v["case"]) - max(v["control"]), 6) == 0.20
    # a non-planted probe (cg00000010): no group difference
    v = _by_group("cg00000010")
    assert max(v["case"]) == max(v["control"]) and min(v["case"]) == min(v["control"])
