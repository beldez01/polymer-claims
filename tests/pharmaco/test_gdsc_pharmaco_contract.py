from polymer_claims import contracts
from polymer_claims.ingest.gdsc_pharmaco import build_pharmaco_contract

def test_build_pharmaco_contract_roundtrips(tmp_path):
    lines = ["L1", "L2", "L3", "L4"]
    betas = {"CDKN2A": dict(zip(lines, [0.1, 0.2, 0.8, 0.9])),
             "MTAP":   dict(zip(lines, [0.15, 0.25, 0.75, 0.85]))}
    aucs = {"Palbociclib": dict(zip(lines, [0.95, 0.90, 0.55, 0.50]))}
    tissue = {"L1": "skin", "L2": "skin", "L3": "lung", "L4": "lung"}
    uid = build_pharmaco_contract(betas, aucs, tissue,
                                  genes=["CDKN2A", "MTAP"], drugs=["Palbociclib"],
                                  out_dir=tmp_path)
    assert uid == "gdsc_pharmaco@1"
    contracts.clear_contract_cache()
    # feature rows are prefixed; tissue rides col_data as Sample_Group
    manifest_p = tmp_path / "gdsc_pharmaco.json"
    text = manifest_p.read_text()
    assert "meth::CDKN2A" in text and "auc::Palbociclib" in text
    assert '"Sample_Group": "skin"' in text
