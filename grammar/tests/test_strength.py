from polymer_grammar.strength import AXES, StrengthVector, licensed


def _v(**kw):
    base = dict(
        magnitude=0.5, uncertainty=0.5, evidence_against_null=0.5,
        severity=0.5, world_contact=0.5, explanatory_virtue=0.5,
    )
    base.update(kw)
    return StrengthVector(**base)


def test_axes_are_the_six():
    assert AXES == (
        "magnitude", "uncertainty", "evidence_against_null",
        "severity", "world_contact", "explanatory_virtue",
    )


def test_meet_is_componentwise_min():  # AND = weakest link
    a = _v(magnitude=0.9, severity=0.2)
    b = _v(magnitude=0.3, severity=0.8)
    m = a.meet(b)
    assert m.magnitude == 0.3
    assert m.severity == 0.2


def test_join_is_componentwise_max():  # OR
    a = _v(magnitude=0.9, severity=0.2)
    b = _v(magnitude=0.3, severity=0.8)
    j = a.join(b)
    assert j.magnitude == 0.9
    assert j.severity == 0.8


def test_dominance_and_incomparability():
    strong = _v(magnitude=0.9, severity=0.9)
    weak = _v(magnitude=0.4, severity=0.4)
    assert strong.dominates(weak)
    assert not weak.dominates(strong)
    assert strong.comparable(weak)

    # trade-off -> genuinely incomparable
    a = _v(magnitude=0.9, severity=0.2)
    b = _v(magnitude=0.2, severity=0.9)
    assert not a.dominates(b)
    assert not b.dominates(a)
    assert not a.comparable(b)


def test_licensed_requires_dominating_threshold_on_every_axis():
    threshold = _v(**{ax: 0.6 for ax in AXES})
    passing = _v(**{ax: 0.7 for ax in AXES})
    one_short = passing.model_copy(update={"severity": 0.5})
    assert licensed(passing, threshold)
    assert not licensed(one_short, threshold)  # fails on the single low axis
