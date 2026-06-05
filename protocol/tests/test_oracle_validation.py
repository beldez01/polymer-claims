from __future__ import annotations

from polymer_grammar import OracleDossier, StrengthVector, ValidationTier

from polymer_protocol.oracle import OracleRegistry, oracle_cap
from polymer_protocol.oracle_validation import (
    OracleValidationRecord,
    SpotProbe,
    oracle_validation_pass,
)
from tests.conftest import make_claim, make_plan


def _registry(*pairs) -> OracleRegistry:
    return OracleRegistry(
        dossiers=tuple(OracleDossier(oracle_id=oid, validation_tier=t) for oid, t in pairs)
    )


def _tier(registry, oracle_id):
    return registry.resolve(oracle_id).validation_tier


def test_failing_oracle_is_decayed_in_new_registry():
    reg = _registry(("o1", ValidationTier.GOLD))
    probes = (
        SpotProbe(oracle_id="o1", passed=True),
        SpotProbe(oracle_id="o1", passed=False),  # 1/2 pass -> floor(0.5*4)=2 BENCHMARKED
    )
    reg2, rec = oracle_validation_pass(reg, probes=probes)
    assert _tier(reg2, "o1") == ValidationTier.BENCHMARKED
    assert _tier(reg, "o1") == ValidationTier.GOLD  # original untouched (pure)
    d = rec.decays[0]
    assert (d.oracle_id, d.probes_run, d.probes_passed) == ("o1", 2, 1)
    assert d.tier_before == ValidationTier.GOLD and d.tier_after == ValidationTier.BENCHMARKED


def test_fully_passing_oracle_unchanged_but_recorded():
    reg = _registry(("o1", ValidationTier.ANCHORED))
    reg2, rec = oracle_validation_pass(reg, probes=(SpotProbe(oracle_id="o1", passed=True),))
    assert _tier(reg2, "o1") == ValidationTier.ANCHORED
    d = rec.decays[0]
    assert d.tier_before == d.tier_after == ValidationTier.ANCHORED


def test_oracle_with_no_probes_is_untouched_and_not_recorded():
    reg = _registry(("o1", ValidationTier.GOLD), ("o2", ValidationTier.GOLD))
    reg2, rec = oracle_validation_pass(reg, probes=(SpotProbe(oracle_id="o1", passed=False),))
    assert _tier(reg2, "o2") == ValidationTier.GOLD
    assert [d.oracle_id for d in rec.decays] == ["o1"]


def test_probe_for_unknown_oracle_is_recorded_not_applied():
    reg = _registry(("o1", ValidationTier.GOLD))
    reg2, rec = oracle_validation_pass(
        reg, probes=(SpotProbe(oracle_id="ghost", passed=False),)
    )
    assert rec.unknown_oracle_ids == ("ghost",)
    assert rec.decays == ()
    assert reg2 is reg  # nothing in the registry changed -> same object


def test_pass_is_deterministic_and_sorted():
    reg = _registry(("b", ValidationTier.GOLD), ("a", ValidationTier.GOLD))
    probes = (SpotProbe(oracle_id="b", passed=False), SpotProbe(oracle_id="a", passed=False))
    r1, rec1 = oracle_validation_pass(reg, probes=probes)
    r2, rec2 = oracle_validation_pass(reg, probes=probes)
    assert rec1 == rec2
    assert [d.oracle_id for d in rec1.decays] == ["a", "b"]  # sorted


def test_decayed_registry_tightens_oracle_cap_end_to_end():
    # The headline property: a decayed registry makes oracle_cap bite harder through the #2 seam.
    strong = StrengthVector(magnitude=0.9, certainty=0.8, evidence_against_null=0.9,
                            severity=0.9, world_contact=0.9, explanatory_virtue=0.9)
    claim = make_claim("c", plan=make_plan(0.01, 0.05, oracle_ref="o1"), strength=strong)
    reg = _registry(("o1", ValidationTier.GOLD))
    before = oracle_cap(claim, reg)
    assert before == strong  # GOLD caps nothing
    reg2, _ = oracle_validation_pass(reg, probes=(SpotProbe(oracle_id="o1", passed=False),))  # 0% -> UNVALIDATED
    after = oracle_cap(claim, reg2)
    assert after.magnitude < before.magnitude        # goodness axis capped down
    assert after.certainty < before.certainty        # certainty (goodness axis) capped down (F2)


def test_empty_probes_returns_same_registry():
    reg = _registry(("o1", ValidationTier.GOLD))
    reg2, rec = oracle_validation_pass(reg, probes=())
    assert reg2 is reg
    assert rec == OracleValidationRecord()


def test_oracle_validation_symbols_are_exported_from_package():
    import polymer_protocol as pp

    assert hasattr(pp, "oracle_validation_pass")
    assert hasattr(pp, "SpotProbe")
    assert hasattr(pp, "OracleDecay")
    assert hasattr(pp, "OracleValidationRecord")
