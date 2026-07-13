"""Thin CLI: drive the PRE-REGISTERED TE-family n-DMP sweep over the REAL Loyfer 2023 WGBS atlas.

Not exercised by tests (points at the real atlas + rmsk on disk; each family rescans ~47 sample BEDs,
so the whole panel is several minutes). Contrasts Lymphoid vs Myeloid lineages across each TE subfamily
in te_ndmp.PANEL through ONE shared e-LOND ledger and prints the honest per-family verdicts + numbers,
then writes a JSON summary next to the contracts. Real betas/contracts stay local (scratch cache dir;
nothing real is committed).

Usage:  uv run python scripts/rip_te_families_ndmp.py [out_summary.json]
"""
import json
import sys
from dataclasses import asdict
from pathlib import Path

from polymer_claims.io import dump_corpus
from polymer_claims.te_ndmp import run_te_family_sweep

_ATLAS = Path.home() / "Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"
_RMSK = Path.home() / "Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt"
_REPO_ROOT = Path(__file__).resolve().parents[1]
_BUNDLE_PATH = _REPO_ROOT / "data" / "demo" / "transposable_elements_universe.json"


def main() -> None:
    contracts_dir = Path.home() / ".cache/polymer-claims/te_ndmp_contracts"
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (contracts_dir / "te_sweep_summary.json")

    res = run_te_family_sweep(
        _RMSK,
        _ATLAS / "bed_hg38",
        _ATLAS / "sample_manifest.tsv",
        contracts_dir,
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, min_cov=4, target_fdr=0.05,
    )

    print("\n=== TE-family n-DMP sweep — Lymphoid vs Myeloid (Loyfer 2023 WGBS atlas) ===")
    print(f"shared e-LOND ledger, target_fdr=0.05; {len(res.families)} pre-registered families\n")
    hdr = f"{'family':<18}{'elems':>8}{'probes':>8}{'k':>5}{'t-leg':>7}{'rank':>6}{'e-value':>14}{'bar':>10}  verdict"
    print(hdr)
    print("-" * len(hdr))
    for f in res.families:
        ev = "n/a" if f.e_value is None else f"{f.e_value:.3g}"
        bar = "n/a" if f.bar is None else f"{f.bar:.3g}"
        print(f"{f.key:<18}{f.n_windows:>8}{f.n_probes:>8}{f.k:>5}{f.count_ttest:>7}{f.count_rank:>6}"
              f"{ev:>14}{bar:>10}  {f.verdict}")
    if res.excluded:
        print("\nexcluded (logged, not silently dropped):")
        for name, why in res.excluded:
            print(f"  {name}: {why}")

    n_lic = sum(1 for f in res.families if f.verdict == "LICENSED")
    print(f"\nLICENSED: {n_lic}/{len(res.families)}   ledger discoveries: {res.corpus.fdr_ledger.n_discoveries}")

    # Emit the strict-Corpus arm bundle (claims + e-values + shared ledger; NO raw betas — those stay
    # in the local SE-Contracts). This is the committable artifact a `collect_transposable_elements`
    # collector loads via io.load_corpus.
    _BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _BUNDLE_PATH.write_text(dump_corpus(res.corpus))
    print(f"arm bundle -> {_BUNDLE_PATH}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "contrast": {"group_col": "lineage", "level_a": "Lymphoid", "level_b": "Myeloid"},
        "alpha": 0.05, "target_fdr": 0.05,
        "families": [asdict(f) | {"status": f.status.value} for f in res.families],
        "excluded": [{"family": n, "reason": w} for n, w in res.excluded],
        "n_licensed": n_lic, "n_discoveries": res.corpus.fdr_ledger.n_discoveries,
    }
    out_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nsummary -> {out_path}")


if __name__ == "__main__":
    main()
