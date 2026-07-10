"""Thin CLI: drive the HERV-K(HML-2) LTR5_Hs n-DMP count claim over the REAL Loyfer 2023 WGBS atlas.

Not exercised by tests (points at the real atlas + rmsk on disk; gathering CpGs across thousands of
scattered LTR5_Hs elements is several minutes). Contrasts Lymphoid vs Myeloid lineages and prints the
honest verdict + numbers. Real betas/contracts stay local (contracts_dir is a scratch dir; nothing
real is committed).
"""
from pathlib import Path

from polymer_claims.rip_hervk_ndmp import run_hervk_ndmp

_ATLAS = Path.home() / "Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"
_RMSK = Path.home() / "Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt"


def main() -> None:
    contracts_dir = Path.home() / ".cache/polymer-claims/hervk_ndmp_contracts"
    res = run_hervk_ndmp(
        _RMSK,
        _ATLAS / "bed_hg38",
        _ATLAS / "sample_manifest.tsv",
        contracts_dir,
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, min_cov=4,
    )
    print(f"HERV-K LTR5_Hs elements (windows): {res.n_windows}")
    print(f"N complete-case probes: {res.n_probes}")
    print(f"pre-registered k (>=3x chance): {res.k}")
    print(f"observed DMP count  leg A (pooled-t): {res.count_ttest}")
    print(f"observed DMP count  leg B (rank-sum): {res.count_rank}")
    print(f"count e-value: {res.e_value}")
    print(f"slot-1 e-LOND bar (1/alpha_1): {res.slot1_bar}")
    print(f"VERDICT: {res.verdict}")


if __name__ == "__main__":
    main()
