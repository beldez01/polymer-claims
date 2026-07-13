"""Validity control for the TE-family n-DMP strain: does the gate license real lineage signal, or
would it fire on ANY large probe set?

For the strongest (HERV-K) and weakest (AluYa5) families, count DMPs with the REAL Lymphoid/Myeloid
labels vs. several deterministic PERMUTATIONS of those labels. Under a valid gate the permuted count
must collapse toward chance (~alpha*N = 5% of probes); a real lineage effect shows the true count far
above that. If permuted counts stayed high, the "6/6 LICENSED" result would be an artifact, not signal.

Not a test (real atlas on disk); run: uv run python scripts/check_te_permutation_null.py
"""
import random
from pathlib import Path

from polymer_grammar import Comparator, MaterializationContext

from polymer_claims.contracts import clear_contract_cache, using_contract_root
from polymer_claims.ingest.build_cpg_matrix_contract import build_cpg_matrix_contract
from polymer_claims.ingest.loyfer_wgbs import CpgMatrix, extract_cpg_matrices_multi_families
from polymer_claims.ingest.te_loci import te_family_windows_multi
from polymer_claims.methyl_ndmp import NDmpRankAdapter, NDmpTTestAdapter, n_dmps_claim

_ATLAS = Path.home() / "Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"
_RMSK = Path.home() / "Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt"
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="loyfer_2023@1")
_SPECS = [("hervk_ltr5", "LTR5_Hs", "LTR"), ("aluya5", "AluYa5", "SINE")]
_N_PERM = 5


def _count_dmps(matrix, uid, contracts_dir, alpha=0.05):
    build_cpg_matrix_contract(matrix, uid, contracts_dir, group_col="lineage")
    claim = n_dmps_claim(
        f"perm-{uid}", ref=f"se:{uid}", probes=tuple(matrix.probe_ids),
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


def _permuted(matrix, rng):
    lineages = [m["lineage"] for m in matrix.sample_meta]
    rng.shuffle(lineages)
    meta = [dict(m, lineage=ln) for m, ln in zip(matrix.sample_meta, lineages)]
    return CpgMatrix(matrix.probe_ids, matrix.samples, meta, matrix.betas)


def main():
    contracts_dir = Path.home() / ".cache/polymer-claims/te_perm_contracts"
    fam_windows = te_family_windows_multi(_RMSK, _SPECS)
    matrices = extract_cpg_matrices_multi_families(
        _ATLAS / "bed_hg38", _ATLAS / "sample_manifest.tsv", fam_windows, min_cov=4)

    print(f"\n=== TE n-DMP permutation-null control (Lymphoid vs Myeloid, {_N_PERM} shuffles) ===")
    print(f"{'family':<12}{'N':>6}{'real t/rank':>14}{'chance~5%N':>12}{'perm t (mean)':>15}{'perm rank':>11}")
    for key, _, _ in _SPECS:
        m = matrices[key]
        n = len(m.probe_ids)
        rt, rr = _count_dmps(m, f"te_perm_{key}_real@1", contracts_dir)
        rng = random.Random(1234)
        pts, prs = [], []
        for i in range(_N_PERM):
            pm = _permuted(m, rng)
            pt, pr = _count_dmps(pm, f"te_perm_{key}_shuf{i}@1", contracts_dir)
            pts.append(pt)
            prs.append(pr)
        chance = 0.05 * n
        print(f"{key:<12}{n:>6}{f'{rt}/{rr}':>14}{chance:>12.0f}"
              f"{sum(pts)/len(pts):>15.1f}{sum(prs)/len(prs):>11.1f}")
    print("\nInterpretation: real >> chance and permuted ~ chance => the signal is a REAL lineage effect,")
    print("not an artifact of testing a large probe set. (This does NOT test TE-vs-background enrichment.)")


if __name__ == "__main__":
    main()
