"""CES-0: both real profiles load, are distinct, and hash deterministically."""
from __future__ import annotations

import pytest

from polymer_claims.analysis_profile import content_hash
from polymer_claims.profiles import load_profile


def test_both_profiles_load():
    m = load_profile("pinned_design_epicv2_hg38_v1", "1")
    c = load_profile("canonical_epicv2_hg38_v1", "1")
    assert m.profile_id == "pinned_design_epicv2_hg38_v1"
    assert c.profile_id == "canonical_epicv2_hg38_v1"


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        load_profile("nope", "1")


def test_profiles_agree_on_normalization_differ_on_detection():
    m = load_profile("pinned_design_epicv2_hg38_v1", "1")
    c = load_profile("canonical_epicv2_hg38_v1", "1")
    # they AGREE on normalization (sesame/QCDPB)
    assert (m.norm_package, m.norm_method, m.norm_prep) == (c.norm_package, c.norm_method, c.norm_prep)
    # and DIFFER on the detection regime
    assert (m.detection_threshold, m.detection_rule) != (c.detection_threshold, c.detection_rule)


def test_profiles_have_distinct_deterministic_hashes():
    m1 = content_hash(load_profile("pinned_design_epicv2_hg38_v1", "1"))
    m2 = content_hash(load_profile("pinned_design_epicv2_hg38_v1", "1"))
    c1 = content_hash(load_profile("canonical_epicv2_hg38_v1", "1"))
    assert m1 == m2          # deterministic
    assert m1 != c1          # distinct regimes -> distinct content-address


def test_cross_reactive_pin_is_content_addressed():
    m = load_profile("pinned_design_epicv2_hg38_v1", "1")
    assert m.cross_reactive_n_probes == 12000
    assert m.cross_reactive_file_hash == (
        "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
