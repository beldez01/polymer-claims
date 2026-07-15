"""Builder for se:ebv_lymphoma_expr@1 — EBV+ vs EBV- lymphoma RNA-seq TPM (Ch1b viral lane).

Takes a viral+host expression matrix (features x samples) with an EBV-status grouping and writes a
data contract. The viral transcripts (LMP1/2A, EBNA1/2/3) must have been quantified against a
COMPOSITE GRCh38 + EBV(NC_007605) reference upstream — this builder only packages the resulting
matrix; it does not align reads. Mirrors ingest/tcga_laml_fusion_expr.py. numpy-free.

DATA-GATED: the operator supplies the re-quantified matrix (see DATA-PLAN §2.1); this builder makes
the contract one call. Groups are named `EBV_pos` / `EBV_neg` to match the Ch1b feature claim's
`level_a` / `level_b`.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


def build_ebv_lymphoma_contract(
    tpm: dict[str, dict[str, float]],
    ebv_status: dict[str, str],
    *,
    features: list[str],
    out_dir,
    uid_stem: str = "ebv_lymphoma_expr",
    reference: str = "GRCh38+EBV(NC_007605)",
) -> str:
    """Write se:ebv_lymphoma_expr@1. `features` are transcript/gene keys (e.g. "LMP1", "EBNA1");
    `ebv_status[sample]` ∈ {"EBV_pos","EBV_neg"}. Records the composite reference in the manifest."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    samples = sorted(ebv_status)
    feats = [f"expr::{f}" for f in sorted(features)]

    def _val(f: str, s: str) -> str:
        v = tpm.get(f, {}).get(s)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "nan"
        return f"{float(v):.6f}"

    manifest = {
        "uid": f"{uid_stem}@1",
        "dim": [len(feats), len(samples)],
        "assays": [{"name": "tpm", "ref": f"{uid_stem}.betas.tsv"}],
        "col_data": [
            {"sample_id": s, "Sample_Group": ebv_status[s], "tissue": "lymphoma"}
            for s in samples
        ],
        "row_data": [{"feature_id": f, "chr": "", "pos": 0} for f in feats],
        "metadata": {"source": "EBV+/- lymphoma RNA-seq", "kind": "expression",
                     "genome_assembly": reference,
                     "note": "viral transcripts quantified against a composite host+EBV reference"},
    }
    (out_dir / f"{uid_stem}.json").write_text(json.dumps(manifest, indent=2))

    lines = ["\t".join(["feature_id", *samples])]
    for f in sorted(features):
        lines.append("\t".join([f"expr::{f}", *(_val(f, s) for s in samples)]))
    (out_dir / f"{uid_stem}.betas.tsv").write_text("\n".join(lines) + "\n")
    return f"{uid_stem}@1"
