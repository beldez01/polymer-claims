from __future__ import annotations

from polymer_claims.analysis_profile import content_hash, profile_oracle_id
from polymer_claims.profiles import CANONICAL_EPICV2_V1, CANONICAL_HM450_V1, load_profile


def test_hm450_profile_registered_and_resolvable():
    assert load_profile("canonical_hm450_grch38_v1", "1") is CANONICAL_HM450_V1
    assert profile_oracle_id(CANONICAL_HM450_V1) == "canonical_hm450_grch38_v1@1"


def test_hm450_profile_is_hm450_hg38():
    assert CANONICAL_HM450_V1.array_type == "HM450"
    assert CANONICAL_HM450_V1.genome_assembly == "hg38"


def test_hm450_profile_hash_stable_and_distinct_from_epicv2():
    # deterministic within Python
    assert content_hash(CANONICAL_HM450_V1) == content_hash(CANONICAL_HM450_V1)
    # spans platforms -> a DIFFERENT content-address than the EPICv2 apparatus
    assert content_hash(CANONICAL_HM450_V1) != content_hash(CANONICAL_EPICV2_V1)


def test_hm450_profile_is_honest_about_unadjusted_method():
    # Phase A n-DMP is an unadjusted two-group pooled-t; the apparatus must say so.
    assert CANONICAL_HM450_V1.covariates == ()
    assert CANONICAL_HM450_V1.cell_adjustment is None
    assert CANONICAL_HM450_V1.dmp_method == "two_group_pooled_t"
