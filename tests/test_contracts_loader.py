from __future__ import annotations

import hashlib
import json as _json
from pathlib import Path

import pytest
from pydantic import ValidationError

from polymer_claims._hashing import canonical_sha256
from polymer_claims.contracts import AccessMethod, Checksum, SEContractRef, load_contract


def _ref(**kw) -> SEContractRef:
    base = dict(
        contract_uid="groupdiff_epicv2_demo@1",
        dimnames_hash="sha256:" + "0" * 64,
        assay="beta",
        selection=(("group_col", "Sample_Group"),),
        genome_assembly="hg38",
        self_uri="drs://local/groupdiff_epicv2_demo@1",
        size=123,
        checksums=(Checksum(checksum="ab" * 32),),
        access_methods=(AccessMethod(type="file", access_url="/x/y.tsv"),),
    )
    base.update(kw)
    return SEContractRef(**base)


def test_se_contract_ref_round_trips():
    ref = _ref()
    again = SEContractRef.model_validate(ref.model_dump(mode="json"))
    assert again == ref
    assert again.refget_digest is None  # noted-but-empty slot


def test_se_contract_ref_is_frozen():
    ref = _ref()
    with pytest.raises(ValidationError):
        ref.assay = "counts"  # frozen models reject mutation


# ---------------------------------------------------------------------------
# Loader tests (CES-1 Task 4)
# ---------------------------------------------------------------------------

_REF = "se:groupdiff_epicv2_demo@1"


def test_load_contract_returns_contract_fields():
    ref = load_contract(_REF)
    assert ref.contract_uid == "groupdiff_epicv2_demo@1"
    assert ref.assay == "beta"
    assert ref.genome_assembly == "hg38"
    assert ref.selection  # non-empty selector


def test_load_contract_accepts_bare_ref_without_prefix():
    assert load_contract("groupdiff_epicv2_demo@1") == load_contract(_REF)


def test_dimnames_hash_is_deterministic_and_prefixed():
    h = load_contract(_REF).dimnames_hash
    assert h == load_contract(_REF).dimnames_hash
    assert h.startswith("sha256:")


def test_dimnames_hash_matches_canonical_recipe_over_ordered_ids():
    # parity: the hash is canonical_sha256 over the ORDERED feature/sample id lists.
    contracts_dir = Path(load_contract(_REF).access_methods[0].access_url).parent
    manifest = _json.loads((contracts_dir / "groupdiff_epicv2_demo.json").read_text())
    feature_ids = [r["feature_id"] for r in manifest["row_data"]]
    sample_ids = [c["sample_id"] for c in manifest["col_data"]]
    expected = canonical_sha256({"feature_ids": feature_ids, "sample_ids": sample_ids})
    assert load_contract(_REF).dimnames_hash == expected


def test_dimnames_hash_is_order_sensitive():
    # permuting sample order must change the address (the matrix identity depends on order).
    a = canonical_sha256({"feature_ids": ["cg00000001"], "sample_ids": ["S01", "S02"]})
    b = canonical_sha256({"feature_ids": ["cg00000001"], "sample_ids": ["S02", "S01"]})
    assert a != b


def test_drs_shape_present():
    ref = load_contract(_REF)
    assert ref.self_uri.startswith("drs://")
    assert ref.size > 0
    assert ref.checksums and ref.checksums[0].type == "sha-256"
    assert ref.access_methods and ref.access_methods[0].type == "file"


def test_checksum_is_sha256_over_fixture_bytes():
    ref = load_contract(_REF)
    contracts_dir = Path(ref.access_methods[0].access_url).parent
    manifest_bytes = (contracts_dir / "groupdiff_epicv2_demo.json").read_bytes()
    betas_bytes = (contracts_dir / "groupdiff_epicv2_demo.betas.tsv").read_bytes()
    expected = hashlib.sha256(manifest_bytes + betas_bytes).hexdigest()
    assert ref.checksums[0].checksum == expected
    assert ref.size == len(manifest_bytes) + len(betas_bytes)


def test_unknown_ref_raises_filenotfound():
    with pytest.raises(FileNotFoundError, match="nope"):
        load_contract("se:nope@1")


def test_symbols_reexported_from_umbrella():
    import polymer_claims
    assert hasattr(polymer_claims, "SEContractRef")
    assert hasattr(polymer_claims, "load_contract")
