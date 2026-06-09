from polymer_grammar import Comparator, SatisfactionCriterion

from polymer_protocol.earned_strength import earn_strength


def _crit(comparator, threshold):
    return SatisfactionCriterion(comparator=comparator, threshold=threshold)


def test_gt_margin_drives_evidence_monotonically():
    crit = _crit(Comparator.GT, 10.0)
    weak = earn_strength(11.0, crit, has_real_data=True, agreement=True)   # rel 0.1
    strong = earn_strength(14.0, crit, has_real_data=True, agreement=True)  # rel 0.4
    assert 0.0 < weak.evidence_against_null < strong.evidence_against_null < 1.0


def test_strong_gt_margin_clears_a_two_way_bar():
    # rel_margin 0.4 must earn evidence >= 0.95 so it survives a 2-way BH bar (crit (1/2)*0.1=0.05).
    s = earn_strength(14.0, _crit(Comparator.GT, 10.0), has_real_data=True, agreement=True)
    assert s.evidence_against_null >= 0.95


def test_lt_comparator_is_mirrored():
    crit = _crit(Comparator.LT, 0.05)
    s = earn_strength(0.01, crit, has_real_data=True, agreement=True)  # clears by 0.04/0.05 = 0.8
    assert s.evidence_against_null > 0.99


def test_zero_or_negative_margin_floors_evidence():
    # value does not clear the threshold -> no earned evidence (defensive; caller earns only SATISFIED)
    s = earn_strength(10.0, _crit(Comparator.GT, 10.0), has_real_data=True, agreement=True)
    assert s.evidence_against_null == 0.0


def test_non_ordering_comparator_floors_evidence():
    s = earn_strength(1.0, _crit(Comparator.EQ, 1.0), has_real_data=True, agreement=True)
    assert s.evidence_against_null == 0.0


def test_magnitude_scales_with_value():
    crit = _crit(Comparator.GT, 10.0)
    small = earn_strength(11.0, crit, has_real_data=True, agreement=True)
    big = earn_strength(40.0, crit, has_real_data=True, agreement=True)
    assert small.magnitude < big.magnitude


def test_provenance_and_agreement_toggle_their_axes():
    crit = _crit(Comparator.GT, 10.0)
    real_agreed = earn_strength(14.0, crit, has_real_data=True, agreement=True)
    synth_disagreed = earn_strength(14.0, crit, has_real_data=False, agreement=False)
    assert real_agreed.world_contact == 0.9 and synth_disagreed.world_contact == 0.3
    assert real_agreed.certainty == 0.8 and synth_disagreed.certainty == 0.4


def test_theory_axes_are_fixed_defaults():
    s = earn_strength(14.0, _crit(Comparator.GT, 10.0), has_real_data=True, agreement=True)
    assert s.severity == 0.7
    assert s.explanatory_virtue == 0.5


def test_none_threshold_floors_evidence():
    # Note: SatisfactionCriterion validation requires exactly one of threshold or reference_leaf_index.
    # To test None threshold, create via reference_leaf_index (which leaves threshold as None).
    s = earn_strength(14.0, SatisfactionCriterion(comparator=Comparator.GT, reference_leaf_index=0), has_real_data=True, agreement=True)
    assert s.evidence_against_null == 0.0


def test_public_api_exports():
    import polymer_protocol as pp
    assert hasattr(pp, "earn_strength")
    assert hasattr(pp, "cap_earned")
    from polymer_protocol import cap_earned, earn_strength  # noqa: F401
