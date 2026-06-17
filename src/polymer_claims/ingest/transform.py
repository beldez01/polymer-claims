"""Pure transform helpers: GDC-parsed structures -> SE-Contract pieces.
No network, no numpy import at module load (numpy is lazy-imported only where a large matrix
is assembled in build_contract). Unit-tested on small synthetic fixtures."""
from __future__ import annotations

import json
import math
from pathlib import Path

# IDH hotspot residues that license the IDH_mut grouping (the AML hypermethylation driver).
_IDH_HOTSPOTS = {
    ("IDH1", "R132"),
    ("IDH2", "R140"),
    ("IDH2", "R172"),
}
_SEX_CHROMS = {"chrX", "chrY"}


def case_id(barcode: str) -> str:
    """TCGA barcode -> 12-char case (patient) id, e.g. 'TCGA-AB-2802-03A' -> 'TCGA-AB-2802'.
    Public: the ingest orchestrator joins beta/MAF/clinical records on this case id."""
    return "-".join(barcode.split("-")[:3])


def _is_idh_hotspot(hugo: str, hgvsp_short: str) -> bool:
    """True iff (gene, residue-number) is a licensing IDH hotspot. 'p.R132H' -> ('IDH1','R132')."""
    aa = hgvsp_short[2:] if hgvsp_short.startswith("p.") else hgvsp_short
    # strip the leading ref AA + trailing alt AA -> 'R132H' -> residue token 'R132'
    if len(aa) < 2 or not aa[0].isalpha():
        return False
    i = 1
    while i < len(aa) and aa[i].isdigit():
        i += 1
    residue = aa[:i]  # e.g. 'R132'
    return (hugo, residue) in _IDH_HOTSPOTS


def derive_groups(maf_rows: list[dict], all_case_ids: list[str]) -> dict[str, str]:
    """Each case -> 'IDH_mut' (any IDH hotspot somatic variant) else 'WT'. Cases absent from the
    MAF are 'WT'. Keyed by 12-char case id."""
    mutated: set[str] = set()
    for r in maf_rows:
        if _is_idh_hotspot(r["Hugo_Symbol"], r["HGVSp_Short"]):
            mutated.add(case_id(r["Tumor_Sample_Barcode"]))
    return {cid: ("IDH_mut" if cid in mutated else "WT") for cid in all_case_ids}


def qc_filter(betas: dict[str, dict[str, float]], row_meta: dict[str, dict]) -> list[str]:
    """Genome-wide QC: drop probes with any NaN beta across samples, and sex-chromosome probes.
    Returns the kept probe ids, sorted (deterministic)."""
    kept = []
    for probe, by_sample in betas.items():
        if row_meta.get(probe, {}).get("chr") in _SEX_CHROMS:
            continue
        if any(math.isnan(v) for v in by_sample.values()):
            continue
        kept.append(probe)
    return sorted(kept)


def build_contract(
    out_dir,
    *,
    uid_stem: str = "tcga_laml_idh",
    betas: dict[str, dict[str, float]],
    row_meta: dict[str, dict],
    groups: dict[str, str],
    clinical: dict[str, dict],
    sample_ids: list[str],
) -> str:
    """Assemble + write the SE-Contract (manifest JSON + betas TSV) the existing load_contract reads.
    Probes are the genome-wide QC-passing set (sorted); samples keep caller order. Returns the uid."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    probes = qc_filter(betas, row_meta)  # genome-wide, sorted, deterministic

    manifest = {
        "uid": f"{uid_stem}@1",
        "dim": [len(probes), len(sample_ids)],
        "assays": [{"name": "beta", "ref": f"{uid_stem}.betas.tsv"}],
        "col_data": [
            {
                "sample_id": s,
                "Sample_Group": groups[s],
                "Age": clinical.get(s, {}).get("Age"),
                "Sex": clinical.get(s, {}).get("Sex"),
            }
            for s in sample_ids
        ],
        "row_data": [
            {"feature_id": p, "chr": row_meta[p]["chr"], "pos": row_meta[p]["pos"]}
            for p in probes
        ],
        "metadata": {"genome_assembly": "hg38", "array": "HM450"},
    }
    (out_dir / f"{uid_stem}.json").write_text(json.dumps(manifest, indent=2))

    # betas TSV: header = 'feature_id' + sample ids; one row per probe.
    lines = ["\t".join(["feature_id", *sample_ids])]
    for p in probes:
        row = betas[p]
        lines.append("\t".join([p, *(f"{row[s]:.4f}" for s in sample_ids)]))
    (out_dir / f"{uid_stem}.betas.tsv").write_text("\n".join(lines) + "\n")

    return f"{uid_stem}@1"
