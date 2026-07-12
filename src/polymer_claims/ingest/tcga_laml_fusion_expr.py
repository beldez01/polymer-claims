"""Builder for se:tcga_laml_fusion_expr@1 — TCGA-LAML RNA-seq TPM (4-gene panel) with a t(8;21)
fusion group. Mirrors ingest/gdsc_pharmaco.py:build_pharmaco_contract. Writes a data contract only;
no analysis, no claim (that is Phase 2d-ii). numpy-free (stdlib json/math).
"""
from __future__ import annotations

import json
import math
from pathlib import Path


def build_fusion_expr_contract(
    tpm: dict[str, dict[str, float]],
    fusion_status: dict[str, str],
    karyotype: dict[str, str],
    *,
    genes: list[str],
    out_dir,
    uid_stem: str = "tcga_laml_fusion_expr",
) -> str:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    samples = sorted(fusion_status)
    features = [f"expr::{g}" for g in sorted(genes)]

    def _val(g: str, s: str) -> str:
        v = tpm.get(g, {}).get(s)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "nan"
        return f"{float(v):.6f}"

    manifest = {
        "uid": f"{uid_stem}@1",
        "dim": [len(features), len(samples)],
        "assays": [{"name": "tpm", "ref": f"{uid_stem}.betas.tsv"}],
        "col_data": [
            {
                "sample_id": s,
                "Sample_Group": fusion_status[s],   # loader reads group_col=Sample_Group
                "tissue": "AML",
                "karyotype": karyotype.get(s, ""),  # provenance
            }
            for s in samples
        ],
        "row_data": [{"feature_id": f, "chr": "", "pos": 0} for f in features],
        "metadata": {"source": "TCGA-LAML", "kind": "expression", "genome_assembly": "hg38"},
    }
    (out_dir / f"{uid_stem}.json").write_text(json.dumps(manifest, indent=2))

    lines = ["\t".join(["feature_id", *samples])]
    for g in sorted(genes):
        lines.append("\t".join([f"expr::{g}", *(_val(g, s) for s in samples)]))
    (out_dir / f"{uid_stem}.betas.tsv").write_text("\n".join(lines) + "\n")
    return f"{uid_stem}@1"
