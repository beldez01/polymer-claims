from __future__ import annotations

import polymer_claims.contracts as contracts_mod
from polymer_claims._hashing import canonical_sha256
from polymer_claims.contracts import clear_contract_cache, load_contract
from polymer_claims.ingest.transform import build_contract


def _tiny_inputs():
    sample_ids = ["TCGA-AB-2802", "TCGA-AB-2803", "TCGA-AB-2804", "TCGA-AB-2805"]
    betas = {
        "cg01": {"TCGA-AB-2802": 0.8, "TCGA-AB-2803": 0.82, "TCGA-AB-2804": 0.2, "TCGA-AB-2805": 0.22},
        "cg02": {"TCGA-AB-2802": 0.5, "TCGA-AB-2803": 0.51, "TCGA-AB-2804": 0.49, "TCGA-AB-2805": 0.5},
        "cgX1": {"TCGA-AB-2802": 0.4, "TCGA-AB-2803": 0.4, "TCGA-AB-2804": 0.4, "TCGA-AB-2805": 0.4},  # chrX -> dropped
    }
    row_meta = {
        "cg01": {"chr": "chr1", "pos": 1000},
        "cg02": {"chr": "chr2", "pos": 2000},
        "cgX1": {"chr": "chrX", "pos": 3000},
    }
    groups = {"TCGA-AB-2802": "IDH_mut", "TCGA-AB-2803": "IDH_mut", "TCGA-AB-2804": "WT", "TCGA-AB-2805": "WT"}
    clinical = {
        "TCGA-AB-2802": {"Age": 55, "Sex": "male"},
        "TCGA-AB-2803": {"Age": 60, "Sex": "female"},
        "TCGA-AB-2804": {"Age": 45, "Sex": "male"},
        "TCGA-AB-2805": {"Age": 70, "Sex": "female"},
    }
    return sample_ids, betas, row_meta, groups, clinical


def test_build_contract_round_trips_through_load_contract(tmp_path, monkeypatch):
    sample_ids, betas, row_meta, groups, clinical = _tiny_inputs()
    uid = build_contract(
        tmp_path, betas=betas, row_meta=row_meta, groups=groups,
        clinical=clinical, sample_ids=sample_ids,
    )
    assert uid == "tcga_laml_idh@1"

    # Point the loader at tmp_path and resolve the freshly-written contract.
    monkeypatch.setattr(contracts_mod, "_DIR", tmp_path)
    clear_contract_cache()
    ref = load_contract("se:tcga_laml_idh@1")

    assert ref.genome_assembly == "hg38"
    # the chrX probe was dropped by QC; only cg01,cg02 remain (sorted)
    expected_dimnames = canonical_sha256(
        {"feature_ids": ["cg01", "cg02"], "sample_ids": sample_ids}
    )
    assert ref.dimnames_hash == expected_dimnames
    clear_contract_cache()  # leave the cache clean for other tests
