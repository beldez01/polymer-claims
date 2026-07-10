import gzip
from pathlib import Path
import pytest
from polymer_claims.ingest.loyfer_wgbs import extract_region, extract_regions_multi, SampleBeta

def _write_bed(p: Path, rows):  # rows: (chrom, start, beta, cov)
    with gzip.open(p, "wt") as fh:
        fh.write("#chr\tstart\tend\tbeta\ttotal_cov\ttotal_meth\tn_cpgs\n")
        for chrom, start, beta, cov in rows:
            meth = round(beta * cov)
            fh.write(f"{chrom}\t{start}\t{start+1}\t{beta:.4f}\t{cov}\t{meth}\t1\n")

def _manifest(p: Path, stems):  # stems: (stem, cell_type, broad, lineage)
    lines = ["gsm\tfilename_stem\tcell_type\tcell_type_broad\tlineage\treplicates"]
    for i, (stem, ct, br, ln) in enumerate(stems):
        lines.append(f"G{i}\t{stem}\t{ct}\t{br}\t{ln}\t1_of_1")
    p.write_text("\n".join(lines) + "\n")

def test_extract_region_means_covered_cpgs_and_qc_drops_low_cpg(tmp_path):
    bed_dir = tmp_path / "bed"; bed_dir.mkdir()
    # sample A: 3 CpGs in-window all covered -> mean of 0.8,0.9,0.7 = 0.8
    _write_bed(bed_dir / "A.hg38.bed.gz",
               [("chr6", 100, 0.8, 10), ("chr6", 150, 0.9, 10), ("chr6", 199, 0.7, 10),
                ("chr6", 500, 0.1, 10)])  # out of window
    # sample B: 3 CpGs but 2 below min_cov -> only 1 survives -> dropped (< min_cpg=3)
    _write_bed(bed_dir / "B.hg38.bed.gz",
               [("chr6", 100, 0.2, 10), ("chr6", 150, 0.2, 1), ("chr6", 160, 0.2, 1)])
    man = tmp_path / "manifest.tsv"
    _manifest(man, [("A", "Monocytes", "Monocyte", "Myeloid"),
                    ("B", "T_Naive_CD4", "T_naive", "Lymphoid")])
    out = extract_region(bed_dir, man, "chr6", 100, 200, min_cov=4, min_cpg=3)
    by = {s.sample: s for s in out}
    assert set(by) == {"A"}                      # B QC-dropped
    assert by["A"].n_cpg == 3
    assert by["A"].beta == pytest.approx(0.8)
    assert by["A"].cell_type_broad == "Monocyte"


def test_extract_regions_multi_pulls_all_windows_in_one_pass(tmp_path):
    bed_dir = tmp_path / "bed"; bed_dir.mkdir()
    # sample A: 3 CpGs in chr2 window (mean 0.6), 3 CpGs in chr9 window (mean 0.3)
    _write_bed(bed_dir / "A.hg38.bed.gz",
               [("chr2", 100, 0.5, 10), ("chr2", 150, 0.6, 10), ("chr2", 199, 0.7, 10),
                ("chr9", 500, 0.2, 10), ("chr9", 550, 0.3, 10), ("chr9", 599, 0.4, 10),
                ("chr2", 900, 0.9, 10)])  # out of any window
    # sample B: only chr2 window covered
    _write_bed(bed_dir / "B.hg38.bed.gz",
               [("chr2", 100, 0.1, 10), ("chr2", 150, 0.2, 10), ("chr2", 199, 0.3, 10)])
    man = tmp_path / "manifest.tsv"
    _manifest(man, [("A", "Monocytes", "Monocyte", "Myeloid"),
                    ("B", "T_Naive_CD4", "T_naive", "Lymphoid")])
    out = extract_regions_multi(bed_dir, man,
                                 [("teA", "chr2", 100, 200), ("teB", "chr9", 500, 600)],
                                 min_cov=4, min_cpg=3)
    assert set(out) == {"teA", "teB"}
    a_by = {s.sample: s for s in out["teA"]}
    assert set(a_by) == {"A", "B"}
    assert a_by["A"].beta == pytest.approx(0.6)
    assert a_by["B"].beta == pytest.approx(0.2)
    b_by = {s.sample: s for s in out["teB"]}
    assert set(b_by) == {"A"}
    assert b_by["A"].beta == pytest.approx(0.3)


def test_extract_regions_multi_agrees_with_extract_region(tmp_path):
    bed_dir = tmp_path / "bed"; bed_dir.mkdir()
    _write_bed(bed_dir / "A.hg38.bed.gz",
               [("chr6", 100, 0.8, 10), ("chr6", 150, 0.9, 10), ("chr6", 199, 0.7, 10),
                ("chr6", 500, 0.1, 10)])
    _write_bed(bed_dir / "B.hg38.bed.gz",
               [("chr6", 100, 0.2, 10), ("chr6", 150, 0.2, 1), ("chr6", 160, 0.2, 1)])
    man = tmp_path / "manifest.tsv"
    _manifest(man, [("A", "Monocytes", "Monocyte", "Myeloid"),
                    ("B", "T_Naive_CD4", "T_naive", "Lymphoid")])
    single = extract_region(bed_dir, man, "chr6", 100, 200, min_cov=4, min_cpg=3)
    multi = extract_regions_multi(bed_dir, man, [("w", "chr6", 100, 200)],
                                   min_cov=4, min_cpg=3)["w"]
    assert sorted(single, key=lambda s: s.sample) == sorted(multi, key=lambda s: s.sample)


import os
ATLAS = Path(os.path.expanduser("~/Desktop/PolymerGenomicsAPI/data/wgbs/loyfer_2023"))

@pytest.mark.skipif(not (ATLAS / "bed_hg38").exists(), reason="Loyfer atlas not on disk")
def test_hla_a_promoter_anchor_reproduces_monocyte_open_t_methylated():
    # chr6:29,940,300-29,941,200 GRCh38 — HLA-A upstream promoter SHORE, not the TSS island.
    # Cell-type-variable methylation localizes to the shore; the TSS CpG island stays
    # unmethylated in all lineages, so the prior 4kb window diluted the contrast. The prior
    # 4kb node's reported Δβ≈0.59 was coverage-asymmetry inflated; the real shore Δβ≈0.35.
    out = extract_region(ATLAS / "bed_hg38", ATLAS / "sample_manifest.tsv",
                         "chr6", 29_940_300, 29_941_200, min_cov=4, min_cpg=3)
    mono = [s.beta for s in out if s.cell_type_broad == "Monocyte"]
    tnaive = [s.beta for s in out if s.cell_type_broad == "T_naive"]
    assert mono and tnaive
    mono_m = sum(mono) / len(mono); t_m = sum(tnaive) / len(tnaive)
    assert t_m - mono_m > 0.25            # T methylated, monocyte open (shore Δβ≈0.35, ~2.5×τ)
