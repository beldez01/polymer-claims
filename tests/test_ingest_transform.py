from __future__ import annotations

import math

from polymer_claims.ingest.transform import derive_groups, qc_filter


def test_derive_groups_flags_idh_hotspots():
    maf = [
        {"Hugo_Symbol": "IDH1", "HGVSp_Short": "p.R132H", "Tumor_Sample_Barcode": "TCGA-AB-2802-03A"},
        {"Hugo_Symbol": "IDH2", "HGVSp_Short": "p.R140Q", "Tumor_Sample_Barcode": "TCGA-AB-2803-03A"},
        {"Hugo_Symbol": "IDH2", "HGVSp_Short": "p.R172K", "Tumor_Sample_Barcode": "TCGA-AB-2804-03A"},
        {"Hugo_Symbol": "FLT3", "HGVSp_Short": "p.D835Y", "Tumor_Sample_Barcode": "TCGA-AB-2805-03A"},
        {"Hugo_Symbol": "IDH1", "HGVSp_Short": "p.G123S", "Tumor_Sample_Barcode": "TCGA-AB-2806-03A"},  # non-hotspot
    ]
    cases = ["TCGA-AB-2802", "TCGA-AB-2803", "TCGA-AB-2804", "TCGA-AB-2805", "TCGA-AB-2806", "TCGA-AB-2807"]
    groups = derive_groups(maf, cases)
    assert groups["TCGA-AB-2802"] == "IDH_mut"
    assert groups["TCGA-AB-2803"] == "IDH_mut"
    assert groups["TCGA-AB-2804"] == "IDH_mut"
    assert groups["TCGA-AB-2805"] == "WT"   # FLT3 only
    assert groups["TCGA-AB-2806"] == "WT"   # IDH1 non-hotspot
    assert groups["TCGA-AB-2807"] == "WT"   # no mutation row at all


def test_qc_filter_drops_na_and_sex_chrom_probes():
    betas = {
        "cg01": {"s1": 0.4, "s2": 0.5},          # keep
        "cg02": {"s1": float("nan"), "s2": 0.5}, # drop (NaN)
        "cg03": {"s1": 0.4, "s2": 0.6},          # drop (chrX via row_meta)
        "cg04": {"s1": 0.2, "s2": 0.3},          # keep
    }
    row_meta = {
        "cg01": {"chr": "chr1", "pos": 100},
        "cg02": {"chr": "chr1", "pos": 200},
        "cg03": {"chr": "chrX", "pos": 300},
        "cg04": {"chr": "chr2", "pos": 400},
    }
    kept = qc_filter(betas, row_meta)
    assert kept == ["cg01", "cg04"]
    # determinism
    assert all(not math.isnan(betas[p]["s1"]) for p in kept)
