"""M2 — MHC n-DMP count-enrichment drive.

Two synthetic tests (no real data): (1) the multi-probe contract builder round-trips a tiny CpgMatrix
through `contracts.load_contract` with the right dims + lineage col_data; (2) the driver builds an
n-DMP count claim over a many-probe, strongly-lineage-separated mini-atlas and LICENSES via a genuine
e-LOND discovery at slot 1 (both independent legs clear the pre-registered floor k). The REAL full-MHC
drive is `scripts/rip_mhc_ndmp.py` (points at the on-disk atlas; not exercised here).
"""
from __future__ import annotations

import gzip

from polymer_grammar import Status

from polymer_claims.contracts import (
    clear_contract_cache,
    load_contract,
    load_manifest,
    using_contract_root,
)
from polymer_claims.ingest.build_cpg_matrix_contract import build_cpg_matrix_contract
from polymer_claims.ingest.loyfer_wgbs import CpgMatrix
from polymer_claims.rip_mhc_ndmp import preregistered_k, run_mhc_ndmp


def _meta(sample, lineage):
    return {"sample": sample, "cell_type": f"{lineage}_ct",
            "cell_type_broad": f"{lineage}_broad", "lineage": lineage}


def test_contract_builder_roundtrips_dims_and_lineage(tmp_path):
    # 4 probes x 4 samples (2 Lymphoid / 2 Myeloid), probe p1 cleanly separated.
    samples = ["Ly1", "Ly2", "My1", "My2"]
    meta = [_meta("Ly1", "Lymphoid"), _meta("Ly2", "Lymphoid"),
            _meta("My1", "Myeloid"), _meta("My2", "Myeloid")]
    probes = ["chr6:100", "chr6:200", "chr6:300", "chr6:400"]
    betas = [
        [0.90, 0.88, 0.10, 0.12],   # cleanly separated
        [0.50, 0.52, 0.49, 0.51],
        [0.30, 0.31, 0.33, 0.29],
        [0.70, 0.69, 0.72, 0.71],
    ]
    matrix = CpgMatrix(probe_ids=probes, samples=samples, sample_meta=meta, betas=betas)

    build_cpg_matrix_contract(matrix, "mhc_tiny@1", tmp_path, group_col="lineage")

    with using_contract_root(tmp_path):
        clear_contract_cache()
        se = load_contract("se:mhc_tiny@1")
        manifest = load_manifest(se)
        clear_contract_cache()

    assert manifest["dim"] == [4, 4]
    assert [c["sample_id"] for c in manifest["col_data"]] == samples
    assert [c["lineage"] for c in manifest["col_data"]] == ["Lymphoid", "Lymphoid", "Myeloid", "Myeloid"]
    assert [r["feature_id"] for r in manifest["row_data"]] == probes
    # betas round-trip: the cleanly-separated first probe keeps its values.
    betas_path = se.access_methods[0].access_url
    lines = open(betas_path).read().splitlines()
    assert lines[0].split("\t") == ["feature_id"] + samples
    p1 = next(ln for ln in lines[1:] if ln.startswith("chr6:100")).split("\t")
    assert [float(x) for x in p1[1:]] == [0.90, 0.88, 0.10, 0.12]


def _mini_atlas(tmp_path, *, n_per_group=5, n_probes=12, chrom="chr6", start=1000):
    """A many-probe atlas where EVERY probe strongly separates Lymphoid (~0.9) from Myeloid (~0.1),
    with per-sample jitter so within-group variance is nonzero (a valid t-test)."""
    bed = tmp_path / "bed"
    bed.mkdir()
    positions = [start + 10 * i for i in range(n_probes)]

    def w(stem, base):
        with gzip.open(bed / f"{stem}.hg38.bed.gz", "wt") as fh:
            fh.write("#chr\tstart\tend\tbeta\ttotal_cov\ttotal_meth\tn_cpgs\n")
            for j, pos in enumerate(positions):
                beta = min(0.99, max(0.01, base + 0.003 * j))
                fh.write(f"{chrom}\t{pos}\t{pos+1}\t{beta:.4f}\t20\t{round(beta*20)}\t1\n")

    lines = ["gsm_accession\tfilename_stem\tcell_type\tcell_type_broad\tlineage\treplicates"]
    for i in range(n_per_group):
        w(f"Ly{i}", 0.88 + 0.01 * i)
        w(f"My{i}", 0.10 + 0.01 * i)
        lines.append(f"GLy{i}\tLy{i}\tT_cell\tT_naive\tLymphoid\t{i+1}")
        lines.append(f"GMy{i}\tMy{i}\tMonocytes\tMonocyte\tMyeloid\t{i+1}")
    man = tmp_path / "m.tsv"
    man.write_text("\n".join(lines) + "\n")
    return bed, man, positions


def test_driver_licenses_on_strong_lineage_separation(tmp_path):
    bed, man, positions = _mini_atlas(tmp_path, n_per_group=5, n_probes=12)
    res = run_mhc_ndmp(
        bed, man, tmp_path / "contracts",
        chrom="chr6", start=positions[0], end=positions[-1] + 1,
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, min_cov=4, uid="mhc_ndmp_synth@1",
    )
    assert res.n_probes == 12
    assert res.k == preregistered_k(12, 0.05)  # ceil(3*0.05*12) = 2
    # every probe separates -> both legs count all 12 as DMPs, far above k.
    assert res.count_ttest == 12
    assert res.count_rank == 12
    # LICENSED via a genuine e-LOND discovery at slot 1: e-value clears the slot-1 bar.
    assert res.status == Status.LICENSED
    assert res.verdict == "LICENSED"
    assert res.corpus.fdr_ledger.n_discoveries == 1
    assert res.e_value is not None and res.slot1_bar is not None
    assert res.e_value >= res.slot1_bar
    # credentials on the license are the two ndmp legs.
    c = next(x for x in res.corpus.claims if x.id == "mhc-ndmp")
    cred_ids = {cid for sat in c.licensing.satisfactions for cid in sat.credential_ids}
    assert cred_ids == {"methyl-ndmp-ttest", "methyl-ndmp-rank"}
