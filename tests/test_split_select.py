from __future__ import annotations

import json

import polymer_claims.contracts as contracts_mod
from polymer_claims.contracts import clear_contract_cache, load_contract
from polymer_claims.ingest.transform import build_contract
from polymer_claims.split_select import split_contract, stratified_split


def test_stratified_split_disjoint_covers_all_and_stratified():
    groups = {f"s{i:02d}": ("IDH_mut" if i < 4 else "WT") for i in range(12)}  # 4 IDH_mut, 8 WT
    disc, test = stratified_split(groups)
    assert set(disc).isdisjoint(test)
    assert set(disc) | set(test) == set(groups)
    # each group split ~evenly: 4 IDH_mut -> 2/2, 8 WT -> 4/4
    idh = {s for s, g in groups.items() if g == "IDH_mut"}
    assert len(idh & set(disc)) == 2 and len(idh & set(test)) == 2


def test_stratified_split_is_deterministic():
    groups = {f"s{i:02d}": ("A" if i % 3 == 0 else "B") for i in range(10)}
    assert stratified_split(groups) == stratified_split(groups)
    assert stratified_split(groups)[0] == sorted(stratified_split(groups)[0])  # sorted output


def _planted_contract(tmp_path):
    # 6 samples (2 IDH_mut, 4 WT), 4 probes; cg_hi clearly hypermethylated in IDH_mut.
    sample_ids = ["s1", "s2", "s3", "s4", "s5", "s6"]
    groups = {"s1": "IDH_mut", "s2": "IDH_mut", "s3": "WT", "s4": "WT", "s5": "WT", "s6": "WT"}
    betas = {
        "cg_hi": {"s1": 0.9, "s2": 0.88, "s3": 0.1, "s4": 0.12, "s5": 0.11, "s6": 0.1},
        "cg_lo": {"s1": 0.2, "s2": 0.22, "s3": 0.2, "s4": 0.21, "s5": 0.2, "s6": 0.19},
        "cg_b":  {"s1": 0.5, "s2": 0.52, "s3": 0.5, "s4": 0.49, "s5": 0.5, "s6": 0.51},
        "cg_c":  {"s1": 0.3, "s2": 0.31, "s3": 0.3, "s4": 0.29, "s5": 0.3, "s6": 0.3},
    }
    row_meta = {p: {"chr": "chr1", "pos": 100 + i} for i, p in enumerate(betas)}
    clinical = {s: {"Age": 50, "Sex": "male"} for s in sample_ids}
    build_contract(tmp_path, uid_stem="tcga_laml_idh", betas=betas, row_meta=row_meta,
                   groups=groups, clinical=clinical, sample_ids=sample_ids)
    return sample_ids


def test_split_contract_round_trips_disjoint(tmp_path, monkeypatch):
    _planted_contract(tmp_path)
    disc_ids, test_ids = split_contract(tmp_path)
    assert set(disc_ids).isdisjoint(test_ids)

    monkeypatch.setattr(contracts_mod, "_DIR", tmp_path)
    clear_contract_cache()
    try:
        d = load_contract("se:tcga_laml_idh_disc@1")
        t = load_contract("se:tcga_laml_idh_test@1")
        # same probes, disjoint samples -> different dimnames_hash
        assert d.dimnames_hash != t.dimnames_hash
        dm = json.loads((tmp_path / "tcga_laml_idh_disc.json").read_text())
        tm = json.loads((tmp_path / "tcga_laml_idh_test.json").read_text())
        assert [r["feature_id"] for r in dm["row_data"]] == [r["feature_id"] for r in tm["row_data"]]
        assert {c["sample_id"] for c in dm["col_data"]}.isdisjoint(c["sample_id"] for c in tm["col_data"])
    finally:
        clear_contract_cache()
