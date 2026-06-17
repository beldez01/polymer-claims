from __future__ import annotations

import math

from polymer_claims.ingest.gdc_parse import parse_beta_file, parse_beta_meta, parse_clinical, parse_maf


def test_parse_beta_file_reads_probe_beta_and_na():
    text = "Composite Element REF\tBeta_value\ncg01\t0.83\ncg02\tNA\ncg03\t0.20\n"
    out = parse_beta_file(text)
    assert out["cg01"] == 0.83
    assert math.isnan(out["cg02"])
    assert out["cg03"] == 0.20


def test_parse_beta_file_tolerates_leading_blank_line():
    # a leading blank line must not break header detection (header heuristic = first NON-blank row)
    text = "\nComposite Element REF\tBeta_value\ncg01\t0.7\ncg02\t0.3\n"
    out = parse_beta_file(text)
    assert out == {"cg01": 0.7, "cg02": 0.3}
    assert "Composite Element REF" not in out  # the header row was not parsed as a probe


def test_parse_beta_meta_reads_chr_and_pos_by_name():
    # GDC harmonized beta files carry per-probe Chromosome/Start annotation columns.
    text = (
        "Composite Element REF\tBeta_value\tChromosome\tStart\tGene_Symbol\n"
        "cg01\t0.83\tchr1\t15865\tGENEA\n"
        "cgX9\t0.40\tchrX\t250000\tGENEB\n"
        "cg02\tNA\tchr2\t99\t.\n"
    )
    meta = parse_beta_meta(text)
    assert meta["cg01"] == {"chr": "chr1", "pos": 15865}
    assert meta["cgX9"] == {"chr": "chrX", "pos": 250000}  # sex-chrom probe -> QC can now drop it
    assert meta["cg02"] == {"chr": "chr2", "pos": 99}


def test_parse_beta_meta_defaults_when_no_annotation_columns():
    # a minimal 2-column file (no Chromosome/Start) -> every probe still gets an entry (no KeyError downstream)
    text = "Composite Element REF\tBeta_value\ncg01\t0.5\ncg02\t0.6\n"
    meta = parse_beta_meta(text)
    assert meta["cg01"] == {"chr": "", "pos": 0}
    assert set(meta) == {"cg01", "cg02"}


def test_parse_maf_skips_comments_and_reads_named_columns():
    text = (
        "#version 2.4\n"
        "Hugo_Symbol\tHGVSp_Short\tTumor_Sample_Barcode\n"
        "IDH1\tp.R132H\tTCGA-AB-2802-03A-01D\n"
        "FLT3\tp.D835Y\tTCGA-AB-2805-03A-01D\n"
    )
    rows = parse_maf(text)
    assert len(rows) == 2
    assert rows[0] == {
        "Hugo_Symbol": "IDH1", "HGVSp_Short": "p.R132H",
        "Tumor_Sample_Barcode": "TCGA-AB-2802-03A-01D",
    }


def test_parse_clinical_reads_age_and_sex_by_case():
    text = (
        "case_submitter_id\tage_at_index\tgender\n"
        "TCGA-AB-2802\t55\tmale\n"
        "TCGA-AB-2803\t'--\tfemale\n"
    )
    out = parse_clinical(text)
    assert out["TCGA-AB-2802"] == {"Age": 55, "Sex": "male"}
    assert out["TCGA-AB-2803"] == {"Age": None, "Sex": "female"}
