"""CES-0: both real profiles load, are distinct, and hash deterministically."""
from __future__ import annotations

import pytest

from polymer_claims.analysis_profile import content_hash
from polymer_claims.profiles import load_profile


def test_both_profiles_load():
    m = load_profile("tet2_epicv2_hg38_manuscript", "1")
    c = load_profile("canonical_epicv2_hg38_v1", "1")
    assert m.profile_id == "tet2_epicv2_hg38_manuscript"
    assert c.profile_id == "canonical_epicv2_hg38_v1"


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        load_profile("nope", "1")


def test_profiles_agree_on_normalization_differ_on_detection():
    m = load_profile("tet2_epicv2_hg38_manuscript", "1")
    c = load_profile("canonical_epicv2_hg38_v1", "1")
    # they AGREE on normalization (sesame/QCDPB)
    assert (m.norm_package, m.norm_method, m.norm_prep) == (c.norm_package, c.norm_method, c.norm_prep)
    # and DIFFER on the detection regime
    assert (m.detection_threshold, m.detection_rule) != (c.detection_threshold, c.detection_rule)


def test_profiles_have_distinct_deterministic_hashes():
    m1 = content_hash(load_profile("tet2_epicv2_hg38_manuscript", "1"))
    m2 = content_hash(load_profile("tet2_epicv2_hg38_manuscript", "1"))
    c1 = content_hash(load_profile("canonical_epicv2_hg38_v1", "1"))
    assert m1 == m2          # deterministic
    assert m1 != c1          # distinct regimes -> distinct content-address


def test_cross_reactive_file_hash_is_the_real_wgbs_digest():
    m = load_profile("tet2_epicv2_hg38_manuscript", "1")
    assert m.cross_reactive_n_probes == 11878
    assert m.cross_reactive_file_hash == (
        "sha256:756527d7022855c75a5e0a41895d10c753121b21032c857d159c4bde47fc3013"
    )
