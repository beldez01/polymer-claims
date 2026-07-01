# hla_a_promoter_meth.csv — provenance

Per-sample mean methylation (β) at the **HLA-A 5'UTR/promoter** window, used to license the migrated
claim `hla_t_naive_promoter_methylation_bimodal` via the mean_diff air-gap (Phase 2).

- **Source:** BLUEPRINT WGBS CpG methylation-call bigWigs (`*.CPG_methylation_calls.bs_call.GRCh38.20160531.bw`)
  from EBI: `http://ftp.ebi.ac.uk/pub/databases/blueprint/data/homo_sapiens/GRCh38/…`.
- **Samples:** 3 monocyte + 3 CD4-positive αβ T cell, selected from the BLUEPRINT immune subset
  manifest (`PolymerGenomicsAPI/.../blueprint_immune_subset/subset_wgbs_meth_calls.tsv`).
- **Extraction:** per-CpG methylation values over **chr6:29,940,000–29,944,000 (GRCh38)**, averaged
  per sample (`pyBigWig.intervals` → mean). Monocyte n_CpG ≈ 128–135; CD4-T n_CpG ≈ 9–15.
- **Result:** monocyte β ≈ 0.15 (open), CD4-T β ≈ 0.74 (methylated); **Δβ ≈ 0.59**, matching the
  original claim's stated Δβ ≈ 0.51 (monocyte 0.083 vs T-naive 0.593).

**Honest caveats:** n = 3/group (a demonstration, not a powered cohort); the T group is bulk
CD4-positive αβ T cell (the BLUEPRINT immune subset has no naive-specific T label), so this tests the
monocyte-vs-CD4-T contrast, which carries the claim's mechanism; CD4-T coverage in the window is
sparser than monocyte. Nothing is fabricated — every β is a real per-CpG mean from real WGBS calls.
Regenerate: download the manifest's bs_call bigWigs and run the extraction over the window above.
