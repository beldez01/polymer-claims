"""Builder for se:gtex_healthy@1 — the GTEx healthy-tissue safety atlas (Ch2 `expression::absence`).

Reads the public GTEx v10 gene-median-TPM GCT (genes x tissues) and writes a data contract for a
requested gene panel, with each TISSUE as a sample column (Sample_Group="healthy"). The absence
adapters summarise over all tissues (max / q99) vs a ceiling. Mirrors ingest/tcga_laml_fusion_expr.py.
Writes a data contract only; no analysis, no claim. numpy-free (stdlib gzip/json/math).

Raw GCT (gitignored): `data/gtex/GTEx_v10_gene_median_tpm.gct.gz` (fetched from the GTEx GCS bucket).
"""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path


def _read_gct_panel(gct_path: Path, genes: set[str]) -> tuple[list[str], dict[str, dict[str, float]]]:
    """Return (tissues, {gene_symbol: {tissue: tpm}}) for the requested gene SYMBOLS (GCT Description
    column). First matching row per symbol wins. Genes not present are simply absent from the result."""
    opener = gzip.open if str(gct_path).endswith(".gz") else open
    with opener(gct_path, "rt") as fh:
        fh.readline()                                   # "#1.2"
        fh.readline()                                   # "<nrows>\t<ncols>"
        header = fh.readline().rstrip("\n").split("\t")
        tissues = header[2:]                            # after Name, Description
        out: dict[str, dict[str, float]] = {}
        want = set(genes)
        for line in fh:
            if not want:
                break
            parts = line.rstrip("\n").split("\t")
            sym = parts[1]
            if sym not in want:
                continue
            vals = {}
            for t, v in zip(tissues, parts[2:]):
                try:
                    vals[t] = float(v)
                except ValueError:
                    continue
            out[sym] = vals
            want.discard(sym)                           # first match per symbol
    return tissues, out


def build_gtex_healthy_contract(
    gct_path, *, genes: list[str], out_dir, uid_stem: str = "gtex_healthy",
) -> str:
    """Write se:gtex_healthy@1 for `genes` from the GTEx GCT. Each tissue is a sample column."""
    tissues, panel = _read_gct_panel(Path(gct_path), set(genes))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    kept = [g for g in sorted(genes) if g in panel]     # only genes actually found (never fabricate)
    features = [f"expr::{g}" for g in kept]

    def _val(g: str, t: str) -> str:
        v = panel.get(g, {}).get(t)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "nan"
        return f"{float(v):.6f}"

    manifest = {
        "uid": f"{uid_stem}@1",
        "dim": [len(features), len(tissues)],
        "assays": [{"name": "tpm", "ref": f"{uid_stem}.betas.tsv"}],
        "col_data": [
            {"sample_id": t, "Sample_Group": "healthy", "tissue": t}
            for t in tissues
        ],
        "row_data": [{"feature_id": f, "chr": "", "pos": 0} for f in features],
        "metadata": {"source": "GTEx v10 (gene median TPM)", "kind": "expression",
                     "genome_assembly": "GRCh38", "note": "healthy-tissue safety atlas"},
    }
    (out_dir / f"{uid_stem}.json").write_text(json.dumps(manifest, indent=2))

    lines = ["\t".join(["feature_id", *tissues])]
    for g in kept:
        lines.append("\t".join([f"expr::{g}", *(_val(g, t) for t in tissues)]))
    (out_dir / f"{uid_stem}.betas.tsv").write_text("\n".join(lines) + "\n")
    return f"{uid_stem}@1"
