import json
from pathlib import Path

from polymer_claims.ingest.loyfer_wgbs import SampleBeta
from polymer_claims.ingest.build_loyfer_contract import build_contract


def _rows():
    return [
        SampleBeta("A", "Monocytes", "Monocyte", "Myeloid", 0.15, 40, 12.0),
        SampleBeta("B", "T_Naive_CD4", "T_naive", "Lymphoid", 0.74, 11, 8.0),
        SampleBeta("C", "Monocytes", "Monocyte", "Myeloid", 0.16, 38, 11.0),
    ]


def test_build_contract_writes_schema_and_is_deterministic(tmp_path):
    p1 = build_contract(_rows(), "hla_a_prom@1", tmp_path / "one")
    doc = json.loads(Path(p1).read_text())
    assert doc["uid"] == "hla_a_prom@1"
    assert doc["dim"][1] == 3                          # 3 samples
    assert doc["assays"][0]["ref"] == "hla_a_prom@1.betas.tsv"
    groups = {r["sample_id"]: r["cell_type_broad"] for r in doc["col_data"]}
    assert groups == {"A": "Monocyte", "B": "T_naive", "C": "Monocyte"}
    # determinism: same input -> byte-identical json + betas
    p2 = build_contract(_rows(), "hla_a_prom@1", tmp_path / "two")
    assert Path(p1).read_bytes() == Path(p2).read_bytes()
    assert (tmp_path / "one" / "hla_a_prom@1.betas.tsv").read_bytes() == \
           (tmp_path / "two" / "hla_a_prom@1.betas.tsv").read_bytes()


def test_built_contract_loads_via_load_contract(tmp_path):
    from polymer_claims.contracts import (
        clear_contract_cache, load_contract, using_contract_root,
    )

    build_contract(_rows(), "hla_a_prom@1", tmp_path)
    # load_contract resolves via the _contract_root contextvar (default: the bundled
    # package dir), not cwd -- scope resolution to tmp_path for this call.
    with using_contract_root(tmp_path):
        clear_contract_cache()
        try:
            ref = load_contract("hla_a_prom@1")   # confirm the loader accepts our schema
            assert ref is not None
        finally:
            clear_contract_cache()
