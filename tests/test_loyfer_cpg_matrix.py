import gzip
from pathlib import Path
import pytest
from polymer_claims.ingest.loyfer_wgbs import extract_cpg_matrix, CpgMatrix


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


def test_complete_case_alignment_drops_position_missing_in_one_sample(tmp_path):
    bed_dir = tmp_path / "bed"; bed_dir.mkdir()
    # A and B: pos 100,150,200 all covered. C: pos 150 below min_cov -> excluded genome-wide.
    _write_bed(bed_dir / "A.hg38.bed.gz",
               [("chr6", 100, 0.1, 10), ("chr6", 150, 0.2, 10), ("chr6", 200, 0.3, 10)])
    _write_bed(bed_dir / "B.hg38.bed.gz",
               [("chr6", 100, 0.4, 10), ("chr6", 150, 0.5, 10), ("chr6", 200, 0.6, 10)])
    _write_bed(bed_dir / "C.hg38.bed.gz",
               [("chr6", 100, 0.7, 10), ("chr6", 150, 0.8, 1), ("chr6", 200, 0.9, 10)])
    man = tmp_path / "manifest.tsv"
    _manifest(man, [("A", "Monocytes", "Monocyte", "Myeloid"),
                    ("B", "T_Naive_CD4", "T_naive", "Lymphoid"),
                    ("C", "B_Cells", "B_cell", "Lymphoid")])

    m = extract_cpg_matrix(bed_dir, man, "chr6", 0, 1000, min_cov=4)

    assert isinstance(m, CpgMatrix)
    assert m.probe_ids == ["chr6:100", "chr6:200"]
    assert m.samples == ["A", "B", "C"]
    assert len(m.betas) == 2 and all(len(row) == 3 for row in m.betas)
    assert m.betas[0] == pytest.approx([0.1, 0.4, 0.7])   # pos 100
    assert m.betas[1] == pytest.approx([0.3, 0.6, 0.9])   # pos 200
    lineage_by_sample = {s["sample"]: s["lineage"] for s in m.sample_meta}
    assert lineage_by_sample == {"A": "Myeloid", "B": "Lymphoid", "C": "Lymphoid"}


def test_low_coverage_cpg_in_one_sample_excludes_position_from_complete_case(tmp_path):
    bed_dir = tmp_path / "bed"; bed_dir.mkdir()
    # pos 100 covered in both; pos 150 covered in A but below min_cov in B -> dropped.
    _write_bed(bed_dir / "A.hg38.bed.gz",
               [("chr6", 100, 0.2, 10), ("chr6", 150, 0.9, 10)])
    _write_bed(bed_dir / "B.hg38.bed.gz",
               [("chr6", 100, 0.3, 10), ("chr6", 150, 0.9, 2)])  # cov=2 < min_cov=4
    man = tmp_path / "manifest.tsv"
    _manifest(man, [("A", "Monocytes", "Monocyte", "Myeloid"),
                    ("B", "T_Naive_CD4", "T_naive", "Lymphoid")])

    m = extract_cpg_matrix(bed_dir, man, "chr6", 0, 1000, min_cov=4)

    assert m.probe_ids == ["chr6:100"]
    assert m.betas == [pytest.approx([0.2, 0.3])]
