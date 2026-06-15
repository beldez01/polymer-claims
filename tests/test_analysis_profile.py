"""CES-0: the AnalysisProfile model + its canonical content-address."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from polymer_grammar import ValidationTier

from polymer_claims.analysis_profile import (
    AnalysisProfile,
    content_hash,
    profile_oracle_dossier,
    profile_oracle_id,
    profile_oracle_registry,
    substrate_tier,
)


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
        cross_reactive_source="cross_reactive_probes_v1",
        cross_reactive_file_hash="sha256:abc",
        cross_reactive_n_probes=12000,
        snp_method="sesame:M_SNPcommon_1pt",
        snp_maf=None,
        sex_chrom="removed",
        replicate_collapse="mean_of_variants",
        test_on="M_value",
        clamp_lower=1e-6,
        clamp_upper=0.999999,
        design_formula="~ 0 + Sample_Group + Age + Sex",
        contrast="case - control",
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


def test_profile_oracle_id_is_id_at_version():
    assert profile_oracle_id(_profile(profile_id="abc", version="3")) == "abc@3"


def test_substrate_tier_maps_known_and_defaults_unvalidated():
    assert substrate_tier("wet_lab_anchor") == ValidationTier.ANCHORED
    assert substrate_tier("recomputable_public") == ValidationTier.BENCHMARKED
    assert substrate_tier("literature") == ValidationTier.INDIRECT
    assert substrate_tier("nonsense") == ValidationTier.UNVALIDATED


def test_profile_oracle_dossier_carries_tier_and_domain():
    d = profile_oracle_dossier(_profile(profile_id="abc", version="1"),
                               substrate="recomputable_public")
    assert d.oracle_id == "abc@1"
    assert d.validation_tier == ValidationTier.BENCHMARKED
    assert "genomic_region" in d.applicability_domain.subject_kinds


def test_profile_oracle_registry_holds_each_profiles_dossier():
    reg = profile_oracle_registry(
        (_profile(profile_id="a", version="1"), "recomputable_public"),
        (_profile(profile_id="b", version="1"), "wet_lab_anchor"),
    )
    assert reg.resolve("a@1").validation_tier == ValidationTier.BENCHMARKED
    assert reg.resolve("b@1").validation_tier == ValidationTier.ANCHORED
