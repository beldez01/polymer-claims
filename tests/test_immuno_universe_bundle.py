"""Viewer universe bundle for the two genuinely LICENSED immuno n-DMP nodes (MHC + HERV-K). Synthetic,
fast: exercises `build_bundle` only, not the real drives (those run several minutes; see
viewer/scripts/make_immuno_universe.py's __main__ for the real-bundle build)."""
import json
from pathlib import Path

from viewer.scripts.make_immuno_universe import build_bundle


def test_bundle_renders_two_licensed_nodes(tmp_path):
    nodes = [
        {"id": "mhc_ndmp", "title": "MHC differentially methylated (Lymphoid vs Myeloid)", "status": "LICENSED",
         "tier": "REPRODUCED", "region": "chr6:29900000-33100000", "n_probes": 11582, "dmp_count": 4682,
         "e_value": "inf"},
        {"id": "hervk_ndmp", "title": "HERV-K LTRs differentially methylated (Lymphoid vs Myeloid)",
         "status": "LICENSED", "tier": "REPRODUCED", "region": "HERVK_LTR5_Hs(630 elements)",
         "n_probes": 2587, "dmp_count": 1083, "e_value": "3.25e274"},
    ]
    out = build_bundle(nodes, tmp_path / "immuno_universe.json")
    doc = json.loads(Path(out).read_text())
    ids = {c["id"] for c in doc["claims"]}
    assert ids == {"mhc_ndmp", "hervk_ndmp"}
    by = {c["id"]: c for c in doc["claims"]}
    assert by["mhc_ndmp"]["status"] == "LICENSED"
    assert by["mhc_ndmp"]["e_value"] == "inf"          # inf serialized safely
    for k in ("claims", "defeat_edges", "equivalences", "fdr_ledger"):
        assert k in doc                                 # viewer schema keys present
    json.dumps(doc)                                     # must be JSON-serializable (no float inf)
