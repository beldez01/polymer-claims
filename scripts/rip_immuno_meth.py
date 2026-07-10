"""Thin CLI: drive the immuno/ERV methylation panel over the REAL Loyfer 2023 WGBS atlas.

Not exercised by tests (points at the real atlas on disk). Prints the licensed loci.
"""
from pathlib import Path

from polymer_claims.rip_immuno import run

_ATLAS = Path.home() / "Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"


def main() -> None:
    res = run(
        Path("src/polymer_claims/panels/immuno_meth_lineage_v1.tsv"),
        _ATLAS / "bed_hg38",
        _ATLAS / "sample_manifest.tsv",
        Path("src/polymer_claims/contracts"),
    )
    lic = [k for k, v in res.verdicts.items() if v == "LICENSED"]
    print(f"LICENSED {len(lic)}/{len(res.verdicts)}: {lic}")
    print(f"e-LOND tests registered: {res.corpus.fdr_ledger.n_tests}")


if __name__ == "__main__":
    main()
