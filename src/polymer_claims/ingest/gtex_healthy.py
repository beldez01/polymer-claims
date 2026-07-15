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
    column). FAIL-SAFE for a safety veto (audit finding 5): a symbol with MULTIPLE GCT rows is
    aggregated per-tissue by MAX (never drop the highest-expression row), not "first wins" — so a
    high-expression duplicate can never be silently discarded. Non-numeric cells are skipped and the
    resulting per-gene tissue COVERAGE is recorded by the caller so missingness is auditable."""
    opener = gzip.open if str(gct_path).endswith(".gz") else open
    with opener(gct_path, "rt") as fh:
        fh.readline()                                   # "#1.2"
        fh.readline()                                   # "<nrows>\t<ncols>"
        header = fh.readline().rstrip("\n").split("\t")
        tissues = header[2:]                            # after Name, Description
        out: dict[str, dict[str, float]] = {}
        want = set(genes)
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            sym = parts[1]
            if sym not in want:
                continue
            row = out.setdefault(sym, {})
            for t, v in zip(tissues, parts[2:]):
                try:
                    fv = float(v)
                except ValueError:
                    continue
                if not math.isfinite(fv):               # NaN/inf must not hide a later high finite value
                    continue
                prev = row.get(t)                       # aggregate duplicate rows by MAX (conservative)
                row[t] = fv if prev is None else max(prev, fv)
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
        # coverage per gene: how many of the tissues carry a finite value (audit finding 5 — a safety
        # veto must make missingness visible; a low-coverage gene's max may understate true expression).
        "row_data": [
            {"feature_id": f"expr::{g}", "chr": "", "pos": 0,
             "tissues_covered": len(panel.get(g, {})), "tissues_total": len(tissues)}
            for g in kept
        ],
        "metadata": {"source": "GTEx v10 (gene median TPM)", "kind": "expression",
                     "genome_assembly": "GRCh38",
                     "note": "healthy-tissue safety atlas; duplicate symbols aggregated by MAX; "
                             "check row_data tissues_covered for missingness before trusting a low verdict"},
    }
    (out_dir / f"{uid_stem}.json").write_text(json.dumps(manifest, indent=2))

    lines = ["\t".join(["feature_id", *tissues])]
    for g in kept:
        lines.append("\t".join([f"expr::{g}", *(_val(g, t) for t in tissues)]))
    (out_dir / f"{uid_stem}.betas.tsv").write_text("\n".join(lines) + "\n")
    return f"{uid_stem}@1"
