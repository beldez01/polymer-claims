from polymer_grammar.licensing import (
    MaterializationContext,
    Satisfaction,
    SatisfactionVerdict,
)


def _m(id_="m1"):
    return MaterializationContext(id=id_, api_version="0.9.x", data_version="db@2026-06-01")


def test_materialization_context_carries_version_pins():
    m = _m()
    assert m.api_version == "0.9.x"
    assert m.data_version == "db@2026-06-01"


def test_satisfaction_always_pairs_verdict_with_materialization():
    s = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=_m())
    assert s.verdict == SatisfactionVerdict.SATISFIED
    assert s.materialization.id == "m1"


def test_satisfaction_is_hashable_and_immutable():
    s = Satisfaction(verdict=SatisfactionVerdict.REFUTED, materialization=_m())
    assert isinstance(hash(s), int)


def test_verdict_values():
    assert {v.value for v in SatisfactionVerdict} == {"satisfied", "refuted", "undetermined"}
