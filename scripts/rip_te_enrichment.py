"""Thin CLI: drive the PRE-REGISTERED TE-family BACKGROUND-ENRICHMENT sweep over the REAL Loyfer 2023
WGBS atlas — the honest recast of the n-DMP TE strain.

Step 1 pre-registers the matched-genomic-background lineage-DMP rate from R replicate sets of random
windows (blind to the TE families), exactly the control in check_te_background_enrichment.py, now folded
into a licensable null. Step 2 runs each TE family in te_ndmp.PANEL as a fold-enrichment-over-background
claim through ONE shared e-LOND ledger, and prints the honest verdicts: a family licenses only if its
per-probe lineage-DMP rate clears the background on BOTH legs (fold>=1) AND the count e-value (p0=bg)
clears the e-LOND bar. Expected outcome (see the TE note): young TE families are AT-OR-BELOW baseline, so
few/none license as ENRICHMENT even though all six licensed as beyond-chance n-DMP claims.

Not exercised by tests (real atlas + rmsk on disk; several minutes: R background reps + 6 family passes).
Real betas/contracts stay local (scratch cache dir); only the strict-Corpus arm bundle is committable.

Usage:  uv run python scripts/rip_te_enrichment.py [out_summary.json]
"""
import json
import sys
from dataclasses import asdict
from pathlib import Path

from polymer_claims.io import dump_corpus
from polymer_claims.ingest.te_loci import random_background_windows
from polymer_claims.te_enrichment import estimate_background_dmp_rates, run_te_enrichment_sweep

_ATLAS = Path.home() / "Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"
_RMSK = Path.home() / "Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt"
_REPO_ROOT = Path(__file__).resolve().parents[1]
_BUNDLE_PATH = _REPO_ROOT / "data" / "demo" / "transposable_elements_enrichment_universe.json"

# Matched-background pre-registration (identical knobs to check_te_background_enrichment.py).
_N_REPLICATES = 5
_WINDOWS_PER_REP = 6000
_WINDOW_SIZE = 1500       # bp; sized up vs TE elements since random regions are CpG-sparser


def main() -> None:
    contracts_dir = Path.home() / ".cache/polymer-claims/te_enrichment_contracts"
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (contracts_dir / "te_enrichment_summary.json")

    # --- Step 1: pre-register the matched-genomic-background DMP rate (blind to the TE families) ---
    windows_by_rep = {
        f"bg{i}": random_background_windows(_WINDOWS_PER_REP, _WINDOW_SIZE, seed=1000 + i)
        for i in range(_N_REPLICATES)
    }
    bg_t, bg_r = estimate_background_dmp_rates(
        _ATLAS / "bed_hg38", _ATLAS / "sample_manifest.tsv",
        contracts_dir / "background", windows_by_rep=windows_by_rep,
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid", alpha=0.05, min_cov=4)
    print("\n=== TE background-enrichment sweep — Lymphoid vs Myeloid (Loyfer 2023 WGBS atlas) ===")
    print(f"matched background ({_N_REPLICATES}x{_WINDOWS_PER_REP} random {_WINDOW_SIZE}bp windows): "
          f"t-leg {100*bg_t:.1f}%  rank-leg {100*bg_r:.1f}%\n")

    # --- Step 2: run every TE family as a fold-enrichment claim against that background ---
    res = run_te_enrichment_sweep(
        _RMSK, _ATLAS / "bed_hg38", _ATLAS / "sample_manifest.tsv", contracts_dir,
        bg_rate_ttest=bg_t, bg_rate_rank=bg_r,
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, min_cov=4, target_fdr=0.05)

    hdr = (f"{'family':<18}{'probes':>8}{'t-DMP%':>8}{'fold_t':>8}{'rank-DMP%':>11}{'fold_r':>8}"
           f"{'e-value':>12}{'bar':>9}  verdict")
    print(hdr)
    print("-" * len(hdr))
    for f in res.families:
        tf = 100 * f.count_ttest / f.n_probes if f.n_probes else 0.0
        rf = 100 * f.count_rank / f.n_probes if f.n_probes else 0.0
        ev = "n/a" if f.e_value is None else f"{f.e_value:.3g}"
        bar = "n/a" if f.bar is None else f"{f.bar:.3g}"
        print(f"{f.key:<18}{f.n_probes:>8}{tf:>7.1f}%{f.fold_ttest:>7.2f}x{rf:>10.1f}%{f.fold_rank:>7.2f}x"
              f"{ev:>12}{bar:>9}  {f.verdict}")

    n_lic = sum(1 for f in res.families if f.verdict == "LICENSED")
    print(f"\nLICENSED (ENRICHED above matched background): {n_lic}/{len(res.families)}   "
          f"ledger discoveries: {res.corpus.fdr_ledger.n_discoveries}")
    print("NB: a NON-license here does NOT retract the n-DMP arm's beyond-chance licenses — it means the "
          "family is not ENRICHED over a matched background (differentially methylated != TE-specific hotspot).")

    _BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _BUNDLE_PATH.write_text(dump_corpus(res.corpus))
    print(f"arm bundle -> {_BUNDLE_PATH}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "contrast": {"group_col": "lineage", "level_a": "Lymphoid", "level_b": "Myeloid"},
        "alpha": 0.05, "target_fdr": 0.05,
        "background": {"n_replicates": _N_REPLICATES, "windows_per_rep": _WINDOWS_PER_REP,
                       "window_size_bp": _WINDOW_SIZE, "bg_rate_ttest": bg_t, "bg_rate_rank": bg_r},
        "families": [asdict(f) | {"status": f.status.value} for f in res.families],
        "excluded": [{"family": n, "reason": w} for n, w in res.excluded],
        "n_licensed": n_lic, "n_discoveries": res.corpus.fdr_ledger.n_discoveries,
    }
    out_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"summary -> {out_path}")


if __name__ == "__main__":
    main()
