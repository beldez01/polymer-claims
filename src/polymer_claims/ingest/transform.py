"""Pure transform helpers: GDC-parsed structures -> SE-Contract pieces.
No network, no numpy import at module load (numpy is lazy-imported only where a large matrix
is assembled in build_contract). Unit-tested on small synthetic fixtures."""
from __future__ import annotations

import math

# IDH hotspot residues that license the IDH_mut grouping (the AML hypermethylation driver).
_IDH_HOTSPOTS = {
    ("IDH1", "R132"),
    ("IDH2", "R140"),
    ("IDH2", "R172"),
}
_SEX_CHROMS = {"chrX", "chrY"}


def _case_id(barcode: str) -> str:
    """TCGA barcode -> 12-char case (patient) id, e.g. 'TCGA-AB-2802-03A' -> 'TCGA-AB-2802'."""
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
            mutated.add(_case_id(r["Tumor_Sample_Barcode"]))
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
