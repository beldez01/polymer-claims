# tests/test_contract_root.py
from pathlib import Path
import json
from polymer_claims.contracts import load_contract, using_contract_root


def _write_min_contract(root: Path, uid: str, dimnames_token: str):
    # smallest manifest load_contract accepts (mirror groupdiff_epicv2_demo.json shape)
    stem = uid.split("@")[0]
    (root / f"{stem}.json").write_text(json.dumps({
        "uid": uid, "dim": [1, 2],
        "assays": [{"name": "beta", "ref": f"{stem}.betas.tsv"}],
        "col_data": [{"sample_id": "S01", "Sample_Group": "case"},
                     {"sample_id": "S02", "Sample_Group": "control"}],
        "row_data": [{"feature_id": dimnames_token, "chr": "chr1", "pos": 1}],
        "metadata": {"genome_assembly": "hg38", "array": "EPICv2", "shared_cause_factors": []},
    }))
    (root / f"{stem}.betas.tsv").write_text(f"feature_id\tS01\tS02\n{dimnames_token}\t0.40\t0.20\n")


def test_contextvar_root_resolves_temp_contract(tmp_path):
    _write_min_contract(tmp_path, "synthetic_a@1", "cgAAA")
    with using_contract_root(tmp_path):
        ref = load_contract("se:synthetic_a@1")
    assert ref.contract_uid == "synthetic_a@1"


def test_same_uid_different_root_does_not_alias(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _write_min_contract(a, "dup@1", "cgAAA")
    _write_min_contract(b, "dup@1", "cgBBB")
    with using_contract_root(a):
        ref_a = load_contract("se:dup@1")
    with using_contract_root(b):
        ref_b = load_contract("se:dup@1")
    assert ref_a.dimnames_hash != ref_b.dimnames_hash  # distinct content -> distinct address, no cache alias


def test_default_root_unchanged():
    # a bundled fixture still resolves with no contextvar set (byte-identical behavior)
    ref = load_contract("se:groupdiff_epicv2_demo@1")
    assert ref.contract_uid == "groupdiff_epicv2_demo@1"


def test_temp_root_shadows_a_bundled_uid_then_resets_byte_identical(tmp_path):
    # Highest-risk seam: a temp root holding the SAME uid as a bundled contract must NOT alias the
    # cached bundled one, and after the context exits the bundled resolution must be byte-identical.
    bundled_before = load_contract("se:groupdiff_epicv2_demo@1")
    _write_min_contract(tmp_path, "groupdiff_epicv2_demo@1", "cgSHADOW")  # same uid, different content
    with using_contract_root(tmp_path):
        shadow = load_contract("se:groupdiff_epicv2_demo@1")
    assert shadow.dimnames_hash != bundled_before.dimnames_hash      # temp shadowed the bundled
    bundled_after = load_contract("se:groupdiff_epicv2_demo@1")       # context reset
    assert bundled_after.dimnames_hash == bundled_before.dimnames_hash  # bundled byte-identical again
