import pytest
from polymer_grammar import (
    AXES,
    ApplicabilityDomain,
    Comparator,
    ComputeGraph,
    EvaluationPlan,
    GenomicRegion,
    MeasurementBasis,
    OperationNode,
    OracleDossier,
    ProducedLeafSpec,
    SatisfactionCriterion,
    StrengthVector,
    ValidationTier,
    cap_strength,
    in_domain,
    referenced_oracle_ids,
    tier_ceiling,
    weakest_tier,
)
from pydantic import ValidationError


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
    assert c.uncertainty == 1.0          # no longer a goodness cap; uncertainty is floored in cap_strength
    assert c.evidence_against_null == 0.4
    assert c.world_contact == 0.4
    assert c.severity == 1.0
    assert c.explanatory_virtue == 1.0


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
    assert capped.uncertainty == 0.9          # reverse-polarity floor: max(0.9, 1-0.4=0.6) = 0.9
    assert capped.evidence_against_null == 0.4
    assert capped.world_contact == 0.4
    assert capped.severity == 0.9
    assert capped.explanatory_virtue == 0.9


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
    assert capped.uncertainty == 1.0          # reverse polarity: weak apparatus -> maximally uncertain
    assert capped.severity == 0.7            # untouched
    assert capped.explanatory_virtue == 0.7


def test_cap_strength_weak_tier_raises_uncertainty_not_lowers_it():
    # F2: a precise claim (low uncertainty) evaluated on a weak apparatus must become MORE uncertain.
    precise = StrengthVector(magnitude=0.5, uncertainty=0.1, evidence_against_null=0.5,
                             severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    capped = cap_strength(precise, ValidationTier.BENCHMARKED)  # c=0.6 -> floor 1-0.6=0.4
    assert capped.uncertainty == 0.4           # raised from 0.1, NOT lowered
    assert capped.magnitude == 0.5             # goodness axis below ceiling 0.6 -> unchanged


def test_cap_strength_none_is_none():
    assert cap_strength(None, ValidationTier.GOLD) is None


def test_tier_ceiling_monotone_on_goodness_axes():
    order = [ValidationTier.UNVALIDATED, ValidationTier.INDIRECT,
             ValidationTier.BENCHMARKED, ValidationTier.ANCHORED, ValidationTier.GOLD]
    for ax in ("magnitude", "evidence_against_null", "world_contact"):
        vals = [getattr(tier_ceiling(t), ax) for t in order]
        assert vals == sorted(vals)
        assert vals[0] == 0.0 and vals[-1] == 1.0
    # uncertainty is constant 1.0 in tier_ceiling (capped as a floor in cap_strength, not here)
    assert all(tier_ceiling(t).uncertainty == 1.0 for t in order)


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


def _region():
    return GenomicRegion(
        id="r1", display="chr1:1-100", assembly="GRCh38", chrom="chr1", start=1, end=100
    )


def test_dossier_requires_nonempty_oracle_id():
    with pytest.raises(ValidationError):
        OracleDossier(oracle_id="", validation_tier=ValidationTier.GOLD)


def test_dossier_defaults_unbounded_domain():
    d = OracleDossier(oracle_id="o1", validation_tier=ValidationTier.GOLD)
    assert d.applicability_domain.subject_kinds == ()
    assert d.relative_uncertainty is None


def test_in_domain_unbounded_accepts_anything_including_none():
    dom = ApplicabilityDomain()  # no subject_kinds -> unbounded
    assert in_domain(dom, _region()) is True
    assert in_domain(dom, None) is True


def test_in_domain_bounded_matches_kind():
    dom = ApplicabilityDomain(subject_kinds=("genomic_region",))
    assert in_domain(dom, _region()) is True


def test_in_domain_bounded_rejects_other_kind_and_none():
    dom = ApplicabilityDomain(subject_kinds=("variant_vrs",))
    assert in_domain(dom, _region()) is False   # genomic_region not listed
    assert in_domain(dom, None) is False         # bounded + no subject -> conservative


def _plan_with_refs(*refs):
    nodes = tuple(
        OperationNode(
            id=f"n{i}", impl="builtin::const", params=(("value", "0.0"),),
            produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
            oracle_ref=r,
        )
        for i, r in enumerate(refs)
    )
    return EvaluationPlan(
        graph=ComputeGraph(nodes=nodes, terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
    )


def test_referenced_oracle_ids_collects_non_none():
    plan = _plan_with_refs("api-A", None, "r-engine")
    assert referenced_oracle_ids(plan) == frozenset({"api-A", "r-engine"})


def test_referenced_oracle_ids_empty_when_all_none():
    plan = _plan_with_refs(None, None)
    assert referenced_oracle_ids(plan) == frozenset()


def test_referenced_oracle_ids_dedups_shared_ref():
    plan = _plan_with_refs("o1", "o1", "o2")
    assert referenced_oracle_ids(plan) == frozenset({"o1", "o2"})
