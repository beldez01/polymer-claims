"""M3 — HERV-K(HML-2) LTR5_Hs n-DMP count-enrichment drive (the ERV node).

Three synthetic tests (no real data): (1) extract_cpg_matrix_multi gathers the COMPLETE-CASE union of
CpGs across two windows on different chroms, and AGREES with the trusted single-window extract_cpg_matrix
on one window; (2) hervk_ltr5_windows parses UCSC rmsk columns and keeps only LTR5_Hs/LTR rows on standard
chroms; (3) the driver LICENSES over a many-probe, strongly-lineage-separated multi-window mini-atlas.
The REAL drive is scripts/rip_hervk_ndmp.py (points at the on-disk atlas + rmsk; not exercised here).
"""
from __future__ import annotations

import gzip

from polymer_grammar import Status

from polymer_claims.ingest.hervk_loci import hervk_ltr5_windows
from polymer_claims.ingest.loyfer_wgbs import extract_cpg_matrix, extract_cpg_matrix_multi
from polymer_claims.rip_hervk_ndmp import run_hervk_ndmp
from polymer_claims.rip_mhc_ndmp import preregistered_k


def _write_bed(path, rows):
    """rows: list of (chrom, pos, beta, cov)."""
    with gzip.open(path, "wt") as fh:
        fh.write("#chr\tstart\tend\tbeta\ttotal_cov\ttotal_meth\tn_cpgs\n")
        for chrom, pos, beta, cov in rows:
            fh.write(f"{chrom}\t{pos}\t{pos+1}\t{beta:.4f}\t{cov}\t{round(beta*cov)}\t1\n")


def _manifest(path, entries):
    """entries: list of (stem, lineage)."""
    lines = ["gsm_accession\tfilename_stem\tcell_type\tcell_type_broad\tlineage\treplicates"]
    for stem, lineage in entries:
        lines.append(f"G{stem}\t{stem}\t{lineage}_ct\t{lineage}_broad\t{lineage}\t1")
    path.write_text("\n".join(lines) + "\n")


def test_multi_union_across_two_chroms_and_single_window_agreement(tmp_path):
    bed = tmp_path / "bed"
    bed.mkdir()
    # Sample A and B each cover CpGs in a chr2 window [100,200) AND a chr9 window [500,600).
    # cov>=4 kept. One CpG (chr2:150) is covered in A only -> dropped by complete-case.
    _write_bed(bed / "A.hg38.bed.gz", [
        ("chr2", 100, 0.90, 20), ("chr2", 150, 0.80, 20), ("chr2", 190, 0.70, 20),
        ("chr9", 500, 0.20, 20), ("chr9", 550, 0.10, 20),
        ("chr5", 999, 0.55, 20),  # outside all windows -> ignored
    ])
    _write_bed(bed / "B.hg38.bed.gz", [
        ("chr2", 100, 0.88, 20), ("chr2", 190, 0.72, 20),  # no chr2:150
        ("chr9", 500, 0.22, 20), ("chr9", 550, 0.12, 20),
        ("chr9", 560, 0.30, 2),  # cov<4 -> dropped
    ])
    man = tmp_path / "m.tsv"
    _manifest(man, [("A", "Lymphoid"), ("B", "Myeloid")])

    windows = [("chr2", 100, 200), ("chr9", 500, 600)]
    m = extract_cpg_matrix_multi(bed, man, windows, min_cov=4)
    # complete-case union across BOTH windows: chr2:100, chr2:190, chr9:500, chr9:550 (chr2:150 dropped).
    assert m.probe_ids == ["chr2:100", "chr2:190", "chr9:500", "chr9:550"]
    assert m.samples == ["A", "B"]
    assert m.betas[0] == [0.90, 0.88]   # chr2:100
    assert m.betas[2] == [0.20, 0.22]   # chr9:500

    # AGREEMENT: on a single window the multi path must not diverge from the trusted single-window path.
    single = extract_cpg_matrix(bed, man, "chr2", 100, 200, min_cov=4, require_all_samples=True)
    multi_one = extract_cpg_matrix_multi(bed, man, [("chr2", 100, 200)], min_cov=4)
    assert multi_one.probe_ids == single.probe_ids
    assert multi_one.samples == single.samples
    assert multi_one.betas == single.betas


def test_hervk_ltr5_windows_parses_ucsc_rmsk_columns(tmp_path):
    # Tiny fake rmsk.txt: UCSC column order (0-indexed) genoName=5, genoStart=6, genoEnd=7,
    # repName=10, repClass=11. Two LTR5_Hs/LTR rows + one non-LTR5 row + one non-standard chrom.
    def row(chrom, start, end, rep_name, rep_class):
        # bin swScore milliDiv milliDel milliIns genoName genoStart genoEnd genoLeft strand
        #   repName repClass repFamily repStart repEnd repLeft id
        return "\t".join([
            "595", "8655", "30", "1", "0", chrom, str(start), str(end), "-1", "+",
            rep_name, rep_class, "ERVK", "1", "968", "0", "1",
        ])
    rmsk = tmp_path / "rmsk.txt"
    rmsk.write_text("\n".join([
        row("chr1", 1409806, 1410773, "LTR5_Hs", "LTR"),
        row("chr7", 500, 1400, "LTR5_Hs", "LTR"),
        row("chr1", 2000, 2500, "LTR5A", "LTR"),          # wrong repName -> excluded
        row("chr3", 3000, 3500, "LTR5_Hs", "Simple"),     # wrong repClass -> excluded
        row("chr1_KI270711v1_random", 10, 900, "LTR5_Hs", "LTR"),  # non-standard chrom -> excluded
    ]) + "\n")

    windows = hervk_ltr5_windows(rmsk)
    assert windows == [("chr1", 1409806, 1410773), ("chr7", 500, 1400)]


def _multi_window_atlas(tmp_path, *, n_per_group=5, n_probes_per_win=6):
    """A two-window atlas (chr2 + chr9) where EVERY probe strongly separates Lymphoid (~0.9) from
    Myeloid (~0.1), with per-sample jitter so within-group variance is nonzero (a valid t-test)."""
    bed = tmp_path / "bed"
    bed.mkdir()
    win2 = ("chr2", 1000, 1000 + 10 * n_probes_per_win)
    win9 = ("chr9", 5000, 5000 + 10 * n_probes_per_win)
    pos2 = [1000 + 10 * i for i in range(n_probes_per_win)]
    pos9 = [5000 + 10 * i for i in range(n_probes_per_win)]

    def w(stem, base):
        rows = []
        for j, p in enumerate(pos2):
            rows.append(("chr2", p, min(0.99, max(0.01, base + 0.003 * j)), 20))
        for j, p in enumerate(pos9):
            rows.append(("chr9", p, min(0.99, max(0.01, base + 0.003 * j)), 20))
        _write_bed(bed / f"{stem}.hg38.bed.gz", rows)

    entries = []
    for i in range(n_per_group):
        w(f"Ly{i}", 0.88 + 0.01 * i)
        w(f"My{i}", 0.10 + 0.01 * i)
        entries.append((f"Ly{i}", "Lymphoid"))
        entries.append((f"My{i}", "Myeloid"))
    man = tmp_path / "m.tsv"
    _manifest(man, entries)
    return bed, man, [win2, win9]


def test_driver_licenses_on_strong_lineage_separation(tmp_path, monkeypatch):
    bed, man, windows = _multi_window_atlas(tmp_path, n_per_group=5, n_probes_per_win=6)

    # Feed the two synthetic windows in place of the rmsk parse (no rmsk file needed for this test).
    import polymer_claims.rip_hervk_ndmp as drv
    monkeypatch.setattr(drv, "hervk_ltr5_windows", lambda _p: windows)

    res = run_hervk_ndmp(
        "unused_rmsk_path", bed, man, tmp_path / "contracts",
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, min_cov=4, uid="hervk_ndmp_synth@1",
    )
    assert res.n_windows == 2
    assert res.n_probes == 12  # 6 probes x 2 windows, all complete-case
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
    c = next(x for x in res.corpus.claims if x.id == "hervk-ndmp")
    cred_ids = {cid for sat in c.licensing.satisfactions for cid in sat.credential_ids}
    assert cred_ids == {"methyl-ndmp-ttest", "methyl-ndmp-rank"}
