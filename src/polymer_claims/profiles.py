"""CES-0: the two concrete, versioned AnalysisProfiles + a local resolver.

Mirrors how `datasets/` ships a CSV: a small in-package registry so the local-first slice is
pure and stub-testable with no live R-Engine. Both profiles are EPICv2/hg38 and AGREE on
normalization (sesame/QCDPB); they DIFFER on the detection regime, SNP method, and (manuscript
only) the pinned design formula — proving "which profile" is a named, not defaulted, choice.
"""
from __future__ import annotations

from .analysis_profile import AnalysisProfile

# SHA256 + line count of ~/Desktop/Polymer/R-Engine/data/cross_reactive_epicv2_wgbs.txt
# (Peters 2024 WGBS-validated cross-reactive set; the live cross-project dependency).
_WGBS_HASH = "sha256:756527d7022855c75a5e0a41895d10c753121b21032c857d159c4bde47fc3013"
_WGBS_N = 11878

# The real TET2-manuscript pipeline pinning (audit §3 — ground truth).
TET2_MANUSCRIPT_V1 = AnalysisProfile(
    profile_id="tet2_epicv2_hg38_manuscript",
    version="1",
    array_type="EPICv2",
    genome_assembly="hg38",
    manifest="sesameData::EPICv2.hg38.manifest",
    norm_package="sesame",
    norm_method="openSesame",
    norm_prep="QCDPB",
    detection_threshold=0.80,
    detection_rule="retain_if_rate_ge",
    sample_fail_threshold=None,
    cross_reactive_source="Peters2024_CH_WGBS",
    cross_reactive_file_hash=_WGBS_HASH,
    cross_reactive_n_probes=_WGBS_N,
    snp_method="sesame:M_SNPcommon_1pt",
    snp_maf=None,
    sex_chrom="removed",
    replicate_collapse="mean_of_variants",
    test_on="M_value",
    clamp_lower=1e-6,
    clamp_upper=0.999999,
    design_formula="~ 0 + Sample_Group + Age + Sex",
    contrast="TET2_mut - WT",
    covariates=("Age", "Sex"),
    batch_correction=None,
    cell_adjustment=None,
    dmp_method="limma",
    dmp_adjust_method="BH",
    fdr_threshold=0.05,
    delta_beta_threshold=0.05,
    dmr_method=None,
    seed=None,
    engine_version="sesame/limma/r-4.5.2/bioc-3.22",
)

# The registry canonical_epicv2_hg38_v1 profile (audit §2 — helpers.R:563-570).
CANONICAL_EPICV2_V1 = AnalysisProfile(
    profile_id="canonical_epicv2_hg38_v1",
    version="1",
    array_type="EPICv2",
    genome_assembly="hg38",
    manifest="sesameData::EPICv2.hg38.manifest",
    norm_package="sesame",
    norm_method="openSesame",
    norm_prep="QCDPB",
    detection_threshold=0.05,
    detection_rule="pOOBAH_p_le",
    sample_fail_threshold=0.05,
    cross_reactive_source="Peters2024_CH_WGBS",
    cross_reactive_file_hash=_WGBS_HASH,
    cross_reactive_n_probes=_WGBS_N,
    snp_method="minfi:dropLociWithSnps[SBE,CpG]",
    snp_maf=0.01,
    sex_chrom="removed",
    replicate_collapse="mean_of_variants",
    test_on="M_value",
    clamp_lower=1e-6,
    clamp_upper=0.999999,
    design_formula="~ 0 + group",
    contrast="level2 - level1",
    covariates=(),
    batch_correction=None,
    cell_adjustment=None,
    dmp_method="limma",
    dmp_adjust_method="BH",
    fdr_threshold=0.05,
    delta_beta_threshold=None,
    dmr_method="DMRcate",
    dmr_lambda=1000,
    dmr_c=2,
    dmr_min_cpgs=3,
    seed=None,
    engine_version="sesame/minfi/limma/DMRcate/r-4.5.2/bioc-3.22",
)

_REGISTRY: dict[tuple[str, str], AnalysisProfile] = {
    (p.profile_id, p.version): p for p in (TET2_MANUSCRIPT_V1, CANONICAL_EPICV2_V1)
}


def load_profile(profile_id: str, version: str) -> AnalysisProfile:
    """Resolve a versioned profile from the local registry. KeyError if unknown."""
    try:
        return _REGISTRY[(profile_id, version)]
    except KeyError:
        raise KeyError(f"no profile {profile_id!r}@{version!r} in the CES-0 registry") from None
