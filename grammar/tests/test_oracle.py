from polymer_grammar import (
    AXES,
    StrengthVector,
    ValidationTier,
    cap_strength,
    tier_ceiling,
    weakest_tier,
)


def test_weakest_tier_picks_lowest_rank():
    assert weakest_tier(
        [ValidationTier.GOLD, ValidationTier.INDIRECT, ValidationTier.ANCHORED]
    ) == ValidationTier.INDIRECT


def test_weakest_tier_single():
    assert weakest_tier([ValidationTier.BENCHMARKED]) == ValidationTier.BENCHMARKED


def test_weakest_tier_empty_is_gold_identity():
    # GOLD's ceiling is all-1.0, so "no oracle" -> GOLD -> no cap.
    assert weakest_tier([]) == ValidationTier.GOLD


def test_tier_ceiling_caps_empirical_leaves_theory_at_one():
    c = tier_ceiling(ValidationTier.INDIRECT)
    assert c.magnitude == 0.4
    assert c.uncertainty == 0.4
    assert c.evidence_against_null == 0.4
    assert c.world_contact == 0.4
    assert c.severity == 1.0            # theory axis uncapped
    assert c.explanatory_virtue == 1.0  # theory axis uncapped


def test_tier_ceiling_gold_is_all_one():
    c = tier_ceiling(ValidationTier.GOLD)
    assert all(
        getattr(c, ax) == 1.0
        for ax in ("magnitude", "uncertainty", "evidence_against_null",
                   "severity", "world_contact", "explanatory_virtue")
    )


def test_tier_ceiling_monotone_on_empirical_axis():
    order = [ValidationTier.UNVALIDATED, ValidationTier.INDIRECT,
             ValidationTier.BENCHMARKED, ValidationTier.ANCHORED, ValidationTier.GOLD]
    vals = [tier_ceiling(t).magnitude for t in order]
    assert vals == sorted(vals)
    assert vals[0] == 0.0 and vals[-1] == 1.0


def test_cap_strength_caps_only_empirical():
    s = StrengthVector(magnitude=0.9, uncertainty=0.9, evidence_against_null=0.9,
                       severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    capped = cap_strength(s, ValidationTier.INDIRECT)
    assert capped.magnitude == 0.4
    assert capped.uncertainty == 0.4
    assert capped.evidence_against_null == 0.4
    assert capped.world_contact == 0.4
    assert capped.severity == 0.9            # untouched
    assert capped.explanatory_virtue == 0.9  # untouched


def test_cap_strength_by_gold_is_unchanged():
    s = StrengthVector(magnitude=0.7, uncertainty=0.3, evidence_against_null=0.5,
                       severity=0.6, world_contact=0.2, explanatory_virtue=0.8)
    assert cap_strength(s, ValidationTier.GOLD) == s


def test_cap_strength_by_unvalidated_zeroes_empirical():
    s = StrengthVector(magnitude=0.7, uncertainty=0.7, evidence_against_null=0.7,
                       severity=0.7, world_contact=0.7, explanatory_virtue=0.7)
    capped = cap_strength(s, ValidationTier.UNVALIDATED)
    assert capped.magnitude == 0.0
    assert capped.world_contact == 0.0
    assert capped.severity == 0.7            # untouched
    assert capped.explanatory_virtue == 0.7


def test_cap_strength_none_is_none():
    assert cap_strength(None, ValidationTier.GOLD) is None


def test_tier_ceiling_monotone_on_all_empirical_axes():
    order = [ValidationTier.UNVALIDATED, ValidationTier.INDIRECT,
             ValidationTier.BENCHMARKED, ValidationTier.ANCHORED, ValidationTier.GOLD]
    for ax in ("magnitude", "uncertainty", "evidence_against_null", "world_contact"):
        vals = [getattr(tier_ceiling(t), ax) for t in order]
        assert vals == sorted(vals)
        assert vals[0] == 0.0 and vals[-1] == 1.0


def test_cap_strength_never_raises_an_axis():
    low = StrengthVector(magnitude=0.1, uncertainty=0.1, evidence_against_null=0.1,
                         severity=0.1, world_contact=0.1, explanatory_virtue=0.1)
    capped = cap_strength(low, ValidationTier.GOLD)  # generous tier, but meet is min not max
    for ax in AXES:
        assert getattr(capped, ax) <= getattr(low, ax)


def test_cap_strength_mid_tier_anchored():
    s = StrengthVector(magnitude=0.95, uncertainty=0.95, evidence_against_null=0.95,
                       severity=0.95, world_contact=0.95, explanatory_virtue=0.95)
    capped = cap_strength(s, ValidationTier.ANCHORED)
    assert capped.magnitude == 0.85          # empirical axis capped at the ANCHORED ceiling
    assert capped.severity == 0.95           # theory axis untouched
