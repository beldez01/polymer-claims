from polymer_grammar import (
    CONFIRMATORY_SEVERITY_CEILING,
    SeverityProvenance,
    StrengthVector,
    cap_severity_for_confirmatory,
    severity_provenance_of,
    shared_cause_overlap,
)


def test_overlap_is_set_intersection():
    assert shared_cause_overlap(("a", "b"), ("b", "c")) is True
    assert shared_cause_overlap(("a",), ("c",)) is False
    assert shared_cause_overlap((), ("c",)) is False
    assert shared_cause_overlap(("a",), ()) is False


def test_tier_none_when_no_prior():
    # empty prior_cohorts => inert (None) => byte-identical when off
    assert severity_provenance_of((), ("x",)) is None


def test_tier_confirmatory_on_overlap_else_held_out():
    assert severity_provenance_of(("x",), ("x", "y")) is SeverityProvenance.CONFIRMATORY
    assert severity_provenance_of(("x",), ("y",)) is SeverityProvenance.HELD_OUT
    # prior present but no detectable test cohort => no detected overlap => HELD_OUT
    assert severity_provenance_of(("x",), ()) is SeverityProvenance.HELD_OUT


def _full(severity: float) -> StrengthVector:
    return StrengthVector(
        magnitude=0.9, certainty=0.9, evidence_against_null=0.9,
        severity=severity, world_contact=0.9, explanatory_virtue=0.9,
    )


def test_cap_lowers_only_severity():
    capped = cap_severity_for_confirmatory(_full(0.8))
    assert capped.severity == CONFIRMATORY_SEVERITY_CEILING
    # every other axis byte-unchanged
    for ax in ("magnitude", "certainty", "evidence_against_null", "world_contact", "explanatory_virtue"):
        assert getattr(capped, ax) == 0.9


def test_cap_is_a_floor_min_never_raises_severity():
    already_low = _full(0.05)
    assert cap_severity_for_confirmatory(already_low).severity == 0.05
