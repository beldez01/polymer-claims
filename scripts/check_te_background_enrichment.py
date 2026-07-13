"""Specificity control for the TE-family n-DMP strain: are TE regions ENRICHED for lineage-DMPs, or do
they merely inherit the genome-wide Lymphoid/Myeloid methylation difference?

Draws R replicate sets of random genomic windows (matched-ish in size to TE elements), runs the SAME
n-DMP gate (Lymphoid vs Myeloid), and compares each replicate's lineage-DMP FRACTION to the six TE
families. If the random background shows ~the same DMP fraction as the TE families, the families are at
genomic baseline (differentially methylated but NOT enriched); if the background fraction is much lower,
TEs are genuine hotspots. All R replicates are extracted in ONE atlas pass.

Not a test (real atlas on disk). Run: uv run python scripts/check_te_background_enrichment.py
"""
import json
import statistics
from pathlib import Path

from polymer_grammar import Comparator, MaterializationContext

from polymer_claims.contracts import clear_contract_cache, using_contract_root
from polymer_claims.ingest.build_cpg_matrix_contract import build_cpg_matrix_contract
from polymer_claims.ingest.loyfer_wgbs import extract_cpg_matrices_multi_families
from polymer_claims.ingest.te_loci import random_background_windows
from polymer_claims.methyl_ndmp import NDmpRankAdapter, NDmpTTestAdapter, n_dmps_claim

_ATLAS = Path.home() / "Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="loyfer_2023@1")
_TE_SUMMARY = Path("/tmp/te_sweep/summary.json")

_N_REPLICATES = 5
_WINDOWS_PER_REP = 6000   # random windows per replicate
_WINDOW_SIZE = 1500       # bp; sized up a bit vs TE elements since random regions are CpG-sparser


def _count_dmps(matrix, uid, contracts_dir, alpha=0.05):
    if not matrix.probe_ids:
        return 0, 0
    build_cpg_matrix_contract(matrix, uid, contracts_dir, group_col="lineage")
    claim = n_dmps_claim(
        f"bg-{uid}", ref=f"se:{uid}", probes=tuple(matrix.probe_ids),
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=alpha, k=1.0, comparator=Comparator.GE,
    )
    node = claim.evaluation_plan.graph.nodes[0]
    with using_contract_root(contracts_dir):
        clear_contract_cache()
        try:
            t = int(NDmpTTestAdapter().execute(node, (), _CTX).value)
            r = int(NDmpRankAdapter().execute(node, (), _CTX).value)
        finally:
            clear_contract_cache()
    return t, r


def main():
    contracts_dir = Path.home() / ".cache/polymer-claims/te_bg_contracts"
    fam_windows = {
        f"bg{i}": random_background_windows(_WINDOWS_PER_REP, _WINDOW_SIZE, seed=1000 + i)
        for i in range(_N_REPLICATES)
    }
    matrices = extract_cpg_matrices_multi_families(
        _ATLAS / "bed_hg38", _ATLAS / "sample_manifest.tsv", fam_windows, min_cov=4)

    print("\n=== TE background-enrichment control (Lymphoid vs Myeloid) ===")
    print(f"{_N_REPLICATES} replicates x {_WINDOWS_PER_REP} random {_WINDOW_SIZE}bp windows\n")
    print(f"{'replicate':<12}{'N probes':>10}{'t-DMP%':>9}{'rank-DMP%':>11}")
    t_fracs, r_fracs = [], []
    for i in range(_N_REPLICATES):
        m = matrices[f"bg{i}"]
        n = len(m.probe_ids)
        t, r = _count_dmps(m, f"te_bg_{i}@1", contracts_dir)
        if n:
            tf, rf = 100 * t / n, 100 * r / n
            t_fracs.append(tf)
            r_fracs.append(rf)
            print(f"bg{i:<10}{n:>10}{tf:>8.1f}%{rf:>10.1f}%")
        else:
            print(f"bg{i:<10}{n:>10}{'--':>9}{'--':>11}")

    if t_fracs:
        bt_m, bt_s = statistics.mean(t_fracs), (statistics.stdev(t_fracs) if len(t_fracs) > 1 else 0.0)
        br_m, br_s = statistics.mean(r_fracs), (statistics.stdev(r_fracs) if len(r_fracs) > 1 else 0.0)
        print(f"\nBACKGROUND mean DMP%:  t-leg {bt_m:.1f}% (sd {bt_s:.1f})   rank {br_m:.1f}% (sd {br_s:.1f})")

        if _TE_SUMMARY.exists():
            te = json.load(open(_TE_SUMMARY))["families"]
            print(f"\n{'family':<14}{'t-DMP%':>8}{'fold vs bg':>12}{'rank-DMP%':>11}{'fold vs bg':>12}")
            for f in te:
                n = f["n_probes"]
                tf, rf = 100 * f["count_ttest"] / n, 100 * f["count_rank"] / n
                ft = tf / bt_m if bt_m else float("nan")
                fr = rf / br_m if br_m else float("nan")
                print(f"{f['key']:<14}{tf:>7.1f}%{ft:>11.2f}x{rf:>10.1f}%{fr:>11.2f}x")
            print("\nfold > 1 => TE family is ENRICHED for lineage-DMPs over random genomic background;")
            print("fold ~ 1 => at baseline (differentially methylated, but not a TE-specific hotspot).")


if __name__ == "__main__":
    main()
