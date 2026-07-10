from polymer_claims import contracts
from polymer_claims.ingest.gdsc_pharmaco import build_pharmaco_contract


def test_build_pharmaco_contract_loads_via_load_contract(tmp_path):
    lines = ["L1", "L2", "L3", "L4"]
    betas = {"CDKN2A": dict(zip(lines, [0.1, 0.2, 0.8, 0.9])),
             "MTAP":   dict(zip(lines, [0.15, 0.25, 0.75, 0.85]))}
    aucs = {"Palbociclib": dict(zip(lines, [0.95, 0.90, 0.55, 0.50]))}
    tissue = {"L1": "skin", "L2": "skin", "L3": "lung", "L4": "lung"}
    uid = build_pharmaco_contract(betas, aucs, tissue,
                                  genes=["CDKN2A", "MTAP"], drugs=["Palbociclib"],
                                  out_dir=tmp_path)
    assert uid == "gdsc_pharmaco@1"

    # The whole point of reusing the feature x sample shape: the real loader must read it.
    # (Before genome_assembly was added to metadata, this raised KeyError: 'genome_assembly'.)
    contracts.clear_contract_cache()
    with contracts.using_contract_root(tmp_path):
        se = contracts.load_contract("se:" + uid)
        manifest = contracts.load_manifest(se)

    assert se.contract_uid == "gdsc_pharmaco@1"
    assert se.genome_assembly == "hg38"
    feature_ids = [r["feature_id"] for r in manifest["row_data"]]
    assert "meth::CDKN2A" in feature_ids
    assert "auc::Palbociclib" in feature_ids
    groups = {c["sample_id"]: c["Sample_Group"] for c in manifest["col_data"]}
    assert groups["L1"] == "skin"
