"""Thin CLI: drive the full-MHC n-DMP count claim over the REAL Loyfer 2023 WGBS atlas.

Not exercised by tests (points at the real atlas on disk; extraction is several minutes). Contrasts
Lymphoid vs Myeloid lineages over chr6:29,900,000-33,100,000 and prints the honest verdict + numbers.
Real betas/contracts stay local (contracts_dir is a scratch dir; nothing real is committed).
"""
from pathlib import Path

from polymer_claims.rip_mhc_ndmp import run_mhc_ndmp

_ATLAS = Path.home() / "Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"
# Full MHC window (hg38).
_CHROM, _START, _END = "chr6", 29_900_000, 33_100_000


def main() -> None:
    contracts_dir = Path.home() / ".cache/polymer-claims/mhc_ndmp_contracts"
    res = run_mhc_ndmp(
        _ATLAS / "bed_hg38",
        _ATLAS / "sample_manifest.tsv",
        contracts_dir,
        chrom=_CHROM, start=_START, end=_END,
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, min_cov=4,
    )
    print(f"window {_CHROM}:{_START:,}-{_END:,}")
    print(f"N complete-case probes: {res.n_probes}")
    print(f"pre-registered k (>=3x chance): {res.k}")
    print(f"observed DMP count  leg A (pooled-t): {res.count_ttest}")
    print(f"observed DMP count  leg B (rank-sum): {res.count_rank}")
    print(f"count e-value: {res.e_value}")
    print(f"slot-1 e-LOND bar (1/alpha_1): {res.slot1_bar}")
    print(f"VERDICT: {res.verdict}")


if __name__ == "__main__":
    main()
