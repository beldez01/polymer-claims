"""Content-addressed SE-Contract builder for Loyfer WGBS locus betas: turns a batch of
per-sample SampleBeta rows (Task 1) into a `<uid>.json` + `<uid>.betas.tsv` pair in the
exact schema `polymer_claims.contracts.load_contract` reads (one feature-row -- the locus
mean beta -- x N sample columns)."""
from __future__ import annotations

import json
from pathlib import Path

from .loyfer_wgbs import SampleBeta


def build_contract(
    rows: list[SampleBeta], uid: str, out_dir: Path, *, group_col: str = "cell_type_broad"
) -> Path:
    # group_col names which col_data field downstream tasks should treat as the
    # grouping column; all SampleBeta group-shaped fields (cell_type, cell_type_broad,
    # lineage) are always emitted below, so no branch on group_col is needed here.
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: r.sample)          # deterministic order
    betas_ref = f"{uid}.betas.tsv"
    feature = uid.split("@")[0]

    # .betas.tsv: header = feature_id + sample ids; one row = the locus mean beta per sample
    tsv_lines = ["\t".join(["feature_id"] + [r.sample for r in rows])]
    tsv_lines.append("\t".join([feature] + [f"{r.beta:.6f}" for r in rows]))
    (out / betas_ref).write_text("\n".join(tsv_lines) + "\n")

    doc = {
        "uid": uid,
        "dim": [1, len(rows)],
        "assays": [{"name": "beta", "ref": betas_ref}],
        "col_data": [
            {
                "sample_id": r.sample,
                "cell_type": r.cell_type,
                "cell_type_broad": r.cell_type_broad,
                "lineage": r.lineage,
                "n_cpg": r.n_cpg,
            }
            for r in rows
        ],
        # single-locus feature row; chr/pos unknown at this granularity (mirrors the
        # placeholder convention in ingest/tcga_xena.py's build_real_contract)
        "row_data": [{"feature_id": feature, "chr": "", "pos": 0}],
        "metadata": {
            "genome_assembly": "hg38",  # Loyfer 2023 WGBS atlas is hg38-referenced
        },
    }
    # load_contract resolves the manifest at "<stem>.json" (uid with the "@version"
    # suffix stripped) -- see contracts/__init__.py:_load_contract's `stem = uid.split("@")[0]`.
    # The betas ref keeps the full uid (matches the on-disk fixtures' *_demo.json convention
    # where stem == uid, generalized here since our uid carries a version suffix).
    path = out / f"{feature}.json"
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return path
