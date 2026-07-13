"""extract_cpg_matrices_multi_families: one-pass multi-family extraction MUST equal the proven
per-family extract_cpg_matrix_multi for every family (byte-identical matrices => identical verdicts)."""
from __future__ import annotations

import gzip

from polymer_claims.ingest.loyfer_wgbs import (
    extract_cpg_matrices_multi_families,
    extract_cpg_matrix_multi,
)


def _write_bed(path, rows):
    with gzip.open(path, "wt") as fh:
        fh.write("#chr\tstart\tend\tbeta\ttotal_cov\ttotal_meth\tn_cpgs\n")
        for chrom, pos, beta, cov in rows:
            fh.write(f"{chrom}\t{pos}\t{pos+1}\t{beta:.4f}\t{cov}\t{round(beta*cov)}\t1\n")


def _manifest(path, entries):
    lines = ["gsm_accession\tfilename_stem\tcell_type\tcell_type_broad\tlineage\treplicates"]
    for stem, lineage in entries:
        lines.append(f"G{stem}\t{stem}\t{lineage}_ct\t{lineage}_broad\t{lineage}\t1")
    path.write_text("\n".join(lines) + "\n")


def _mk_atlas(tmp_path):
    bed = tmp_path / "bed"
    bed.mkdir()
    # Family A: chr2:[1000,1100). Family B: chr9:[5000,5100). Some samples miss a family entirely
    # (per-family sample-drop must match). cov<4 dropped; positions not covered in all kept samples
    # dropped by complete-case.
    _write_bed(bed / "S1.hg38.bed.gz", [
        ("chr2", 1000, 0.9, 20), ("chr2", 1050, 0.8, 20),
        ("chr9", 5000, 0.1, 20), ("chr9", 5050, 0.2, 20),
        ("chr5", 42, 0.5, 20),  # in no family window -> ignored
    ])
    _write_bed(bed / "S2.hg38.bed.gz", [
        ("chr2", 1000, 0.88, 20), ("chr2", 1050, 0.82, 20),
        ("chr9", 5000, 0.12, 20), ("chr9", 5050, 0.22, 20),
    ])
    _write_bed(bed / "S3.hg38.bed.gz", [
        ("chr2", 1000, 0.86, 20), ("chr2", 1050, 0.84, 20),
        ("chr2", 1070, 0.7, 2),  # cov<4 -> dropped
        # S3 has NO chr9 CpGs -> must be dropped from family B only
    ])
    man = tmp_path / "m.tsv"
    _manifest(man, [("S1", "Lymphoid"), ("S2", "Myeloid"), ("S3", "Lymphoid")])
    fam = {"A": [("chr2", 1000, 1100)], "B": [("chr9", 5000, 5100)]}
    return bed, man, fam


def test_multi_family_matches_per_family_path(tmp_path):
    bed, man, fam = _mk_atlas(tmp_path)
    multi = extract_cpg_matrices_multi_families(bed, man, fam, min_cov=4)
    for key, windows in fam.items():
        single = extract_cpg_matrix_multi(bed, man, windows, min_cov=4)
        m = multi[key]
        assert m.probe_ids == single.probe_ids, key
        assert m.samples == single.samples, key
        assert m.sample_meta == single.sample_meta, key
        assert m.betas == single.betas, key
    # Family B must have dropped S3 (no chr9 coverage); family A keeps all three samples.
    assert multi["B"].samples == ["S1", "S2"]
    assert multi["A"].samples == ["S1", "S2", "S3"]


def test_overlapping_windows_across_families_route_independently(tmp_path):
    """A CpG inside BOTH families' (overlapping) windows must land in BOTH matrices."""
    bed = tmp_path / "bed"
    bed.mkdir()
    _write_bed(bed / "S1.hg38.bed.gz", [("chr1", 500, 0.3, 10)])
    _write_bed(bed / "S2.hg38.bed.gz", [("chr1", 500, 0.6, 10)])
    man = tmp_path / "m.tsv"
    _manifest(man, [("S1", "Lymphoid"), ("S2", "Myeloid")])
    fam = {"A": [("chr1", 400, 600)], "B": [("chr1", 450, 550)]}
    multi = extract_cpg_matrices_multi_families(bed, man, fam, min_cov=4)
    assert multi["A"].probe_ids == ["chr1:500"]
    assert multi["B"].probe_ids == ["chr1:500"]
    assert multi["A"].betas == multi["B"].betas == [[0.3, 0.6]]
