from __future__ import annotations

import json
import re
from pathlib import Path

_DIR = Path(__file__).resolve().parents[1] / "src" / "polymer_claims" / "contracts"
_MANIFEST = _DIR / "epicv2_casectrl_demo.json"
_BETAS = _DIR / "epicv2_casectrl_demo.betas.tsv"


def _manifest() -> dict:
    return json.loads(_MANIFEST.read_text())


def test_fixture_files_exist():
    assert _MANIFEST.is_file() and _BETAS.is_file()


def test_dims_and_groups():
    m = _manifest()
    nf, ns = m["dim"]
    assert nf == len(m["row_data"]) == 24
    assert ns == len(m["col_data"]) == 100
    groups = [c["Sample_Group"] for c in m["col_data"]]
    assert set(groups) == {"level1", "level2"}
    assert groups.count("level1") == groups.count("level2") == 50


def test_probe_format_and_matrix_shape():
    m = _manifest()
    cg = re.compile(r"^cg\d{8}$")
    ids = [r["feature_id"] for r in m["row_data"]]
    assert all(cg.match(x) for x in ids)
    lines = _BETAS.read_text().splitlines()
    assert lines[0].split("\t") == ["feature_id"] + [c["sample_id"] for c in m["col_data"]]
    assert [ln.split("\t")[0] for ln in lines[1:]] == ids
    assert len(lines) - 1 == 24


def test_metadata_epicv2_hg38():
    m = _manifest()
    assert m["metadata"]["genome_assembly"] == "hg38"
    assert m["metadata"]["array"] == "EPICv2"


def test_planted_shift_on_signal_region_only():
    m = _manifest()
    groups = {c["sample_id"]: c["Sample_Group"] for c in m["col_data"]}
    lines = _BETAS.read_text().splitlines()
    header = lines[0].split("\t")[1:]
    rows = {ln.split("\t")[0]: ln.split("\t")[1:] for ln in lines[1:]}
    ids = [r["feature_id"] for r in m["row_data"]]

    def _delta(probe):
        l1 = [float(v) for sid, v in zip(header, rows[probe]) if groups[sid] == "level1"]
        l2 = [float(v) for sid, v in zip(header, rows[probe]) if groups[sid] == "level2"]
        return sum(l2) / len(l2) - sum(l1) / len(l1)

    for probe in ids[:5]:
        assert round(_delta(probe), 6) == 0.20
    for probe in ids[5:]:
        assert round(_delta(probe), 6) == 0.0
