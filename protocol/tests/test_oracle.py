import pytest
from polymer_grammar import (
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
)
from pydantic import ValidationError

from polymer_protocol import OracleRegistry, oracle_cap
from polymer_protocol.oracle import cap_earned
from tests.conftest import make_claim, make_plan

SV = StrengthVector(magnitude=0.9, certainty=0.1, evidence_against_null=0.9,
                    severity=0.9, world_contact=0.9, explanatory_virtue=0.9)


def _dossier(oid, tier, kinds=()):
    return OracleDossier(
        oracle_id=oid, validation_tier=tier,
        applicability_domain=ApplicabilityDomain(subject_kinds=kinds),
    )


def test_registry_resolve_hit_and_miss():
    reg = OracleRegistry(dossiers=(_dossier("o1", ValidationTier.GOLD),))
    assert reg.resolve("o1").validation_tier == ValidationTier.GOLD
    assert reg.resolve("nope") is None


def test_registry_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        OracleRegistry(dossiers=(_dossier("o1", ValidationTier.GOLD),
                                 _dossier("o1", ValidationTier.INDIRECT)))


def test_oracle_cap_builtin_claim_unchanged():
    c = make_claim("a", strength=SV, plan=make_plan(0.01, 0.05))  # no oracle_ref
    assert oracle_cap(c, OracleRegistry()) == SV


def test_oracle_cap_gold_unchanged():
    c = make_claim("a", strength=SV, plan=make_plan(0.01, 0.05, oracle_ref="g"))
    reg = OracleRegistry(dossiers=(_dossier("g", ValidationTier.GOLD),))
    assert oracle_cap(c, reg) == SV


def test_oracle_cap_unresolved_zeroes_empirical():
    c = make_claim("a", strength=SV, plan=make_plan(0.01, 0.05, oracle_ref="ghost"))
    capped = oracle_cap(c, OracleRegistry())  # unresolved -> UNVALIDATED
    assert capped.magnitude == 0.0 and capped.world_contact == 0.0
    assert capped.severity == 0.9  # theory axis untouched


def test_oracle_cap_out_of_domain_is_unvalidated():
    region = GenomicRegion(id="r1", display="d", assembly="GRCh38", chrom="chr1", start=1, end=9)
    c = make_claim("a", strength=SV, plan=make_plan(0.01, 0.05, oracle_ref="g"), subject=region)
    reg = OracleRegistry(dossiers=(_dossier("g", ValidationTier.GOLD, kinds=("variant_vrs",)),))
    capped = oracle_cap(c, reg)  # region not in domain -> effective UNVALIDATED
    assert capped.magnitude == 0.0


def test_oracle_cap_weakest_of_two_wins():
    nodes = (
        OperationNode(id="n0", impl="builtin::const", params=(("value", "0.01"),),
                      produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
                      oracle_ref="gold"),
        OperationNode(id="n1", impl="builtin::const", params=(("value", "0.0"),),
                      produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
                      oracle_ref="weak"),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=nodes, terminal="n0"),
        criterion=SatisfactionCriterion(comparator=Comparator.LT, threshold=0.05),
    )
    c = make_claim("a", strength=SV, plan=plan)
    reg = OracleRegistry(dossiers=(_dossier("gold", ValidationTier.GOLD),
                                   _dossier("weak", ValidationTier.INDIRECT)))
    capped = oracle_cap(c, reg)
    assert capped.magnitude == 0.4  # weakest (INDIRECT) ceiling wins


def test_oracle_cap_no_plan_returns_strength_unchanged():
    c = make_claim("a", strength=SV)  # no evaluation_plan
    assert c.evaluation_plan is None
    assert oracle_cap(c, OracleRegistry()) == SV


def test_oracle_cap_strengthless_claim_is_none():
    c = make_claim("a", plan=make_plan(0.01, 0.05, oracle_ref="g"))  # strength None
    reg = OracleRegistry(dossiers=(_dossier("g", ValidationTier.GOLD),))
    assert oracle_cap(c, reg) is None


def test_cap_earned_caps_external_strength_by_tier():
    earned = StrengthVector(magnitude=0.95, certainty=0.9, evidence_against_null=0.96,
                            severity=0.7, world_contact=0.9, explanatory_virtue=0.5)
    c = make_claim("a", plan=make_plan(0.01, 0.05, oracle_ref="g"))  # strength None — irrelevant here
    reg = OracleRegistry(dossiers=(_dossier("g", ValidationTier.BENCHMARKED),))
    capped = cap_earned(earned, c, reg)
    assert capped.magnitude == 0.6              # goodness axis capped to BENCHMARKED ceiling
    assert capped.evidence_against_null == 0.6
    assert capped.certainty == 0.6
    assert capped.world_contact == 0.6
    assert capped.severity == 0.7               # theory axis untouched
    assert capped.explanatory_virtue == 0.5


def test_cap_earned_unvalidated_without_registry():
    earned = StrengthVector(magnitude=0.95, certainty=0.9, evidence_against_null=0.96,
                            severity=0.7, world_contact=0.9, explanatory_virtue=0.5)
    c = make_claim("a", plan=make_plan(0.01, 0.05, oracle_ref="g"))
    capped = cap_earned(earned, c, OracleRegistry())  # unresolved -> UNVALIDATED -> 0.0
    assert capped.magnitude == 0.0
    assert capped.severity == 0.7
