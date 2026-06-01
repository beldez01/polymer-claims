import pytest
from pydantic import ValidationError

from polymer_grammar.licensing import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
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


def _sat(id_, verdict=SatisfactionVerdict.SATISFIED):
    return Satisfaction(verdict=verdict, materialization=_m(id_))


def test_severe_test_with_one_satisfied_materialization_builds():
    lic = Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(_sat("m1"),),
                    rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED)
    assert lic.route == LicenseRoute.SEVERE_TEST


def test_replication_requires_two_distinct_materializations():
    ok = Licensing(route=LicenseRoute.REPLICATION,
                   satisfactions=(_sat("m1"), _sat("m2")),
                   rival_set_closure=RivalSetClosure.ONTOLOGY_BOUNDED)
    assert len(ok.satisfactions) == 2
    with pytest.raises(ValidationError):  # only one M
        Licensing(route=LicenseRoute.REPLICATION, satisfactions=(_sat("m1"),),
                  rival_set_closure=RivalSetClosure.ONTOLOGY_BOUNDED)
    with pytest.raises(ValidationError):  # two satisfactions but same M id
        Licensing(route=LicenseRoute.REPLICATION,
                  satisfactions=(_sat("m1"), _sat("m1")),
                  rival_set_closure=RivalSetClosure.ONTOLOGY_BOUNDED)


def test_empty_satisfactions_rejected():
    with pytest.raises(ValidationError):
        Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(),
                  rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED)


def test_non_satisfied_satisfaction_rejected():
    with pytest.raises(ValidationError):
        Licensing(route=LicenseRoute.SEVERE_TEST,
                  satisfactions=(_sat("m1", SatisfactionVerdict.UNDETERMINED),),
                  rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED)


def test_enumerated_closure_requires_named_rivals():
    with pytest.raises(ValidationError):
        Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(_sat("m1"),),
                  rival_set_closure=RivalSetClosure.ENUMERATED)
    ok = Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(_sat("m1"),),
                   rival_set_closure=RivalSetClosure.ENUMERATED,
                   rivals_considered=("MONDO:0005059",))
    assert ok.rivals_considered == ("MONDO:0005059",)


def test_licensing_is_hashable():
    lic = Licensing(route=LicenseRoute.SEVERE_TEST, satisfactions=(_sat("m1"),),
                    rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED)
    assert isinstance(hash(lic), int)
