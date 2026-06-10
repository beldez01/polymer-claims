"""CES-0: the AnalysisProfile model + its canonical content-address."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from polymer_claims.analysis_profile import AnalysisProfile, content_hash


def _profile(**overrides) -> AnalysisProfile:
    base = dict(
        profile_id="p_test",
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
        cross_reactive_file_hash="sha256:abc",
        cross_reactive_n_probes=11878,
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
        dmp_method="limma",
        dmp_adjust_method="BH",
        fdr_threshold=0.05,
        engine_version="sesame@x/limma@y/r-4.5.2",
    )
    base.update(overrides)
    return AnalysisProfile(**base)


def test_profile_is_frozen_and_forbids_extras():
    p = _profile()
    with pytest.raises(ValidationError):
        AnalysisProfile(profile_id="x", version="1", bogus="y")  # missing+extra
    with pytest.raises(ValidationError):
        p.profile_id = "mutated"  # frozen


def test_content_hash_is_deterministic_and_prefixed():
    h1 = content_hash(_profile())
    h2 = content_hash(_profile())
    assert h1 == h2
    assert h1.startswith("sha256:")
    assert len(h1) == len("sha256:") + 64


def test_content_hash_changes_with_any_pinned_field():
    base = content_hash(_profile())
    assert content_hash(_profile(detection_threshold=0.05)) != base
    assert content_hash(_profile(design_formula="~ 0 + Sample_Group")) != base
    assert content_hash(_profile(norm_prep="QCDP")) != base
    assert content_hash(_profile(covariates=("Age",))) != base
