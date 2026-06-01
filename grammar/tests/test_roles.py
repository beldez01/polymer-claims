import pytest
from pydantic import ValidationError

from polymer_grammar.roles import CausalRoles, Role


def test_role_values():
    assert {r.value for r in Role} == {
        "predictor", "outcome", "confounder", "mediator", "collider", "instrument",
    }


def test_causal_roles_builds_and_derives_adjustment_set():
    r = CausalRoles(predictor="curvature", outcome="crossover_rate",
                    confounders=("gc_content",))
    assert r.adjustment_set == frozenset({"gc_content"})


def test_predictor_outcome_must_differ():
    with pytest.raises(ValidationError):
        CausalRoles(predictor="x", outcome="x")


def test_a_variable_cannot_hold_two_roles():
    with pytest.raises(ValidationError):
        CausalRoles(predictor="x", outcome="y", confounders=("z",), mediators=("z",))


def test_adjustment_set_excludes_mediators_colliders_instruments():
    r = CausalRoles(predictor="x", outcome="y", confounders=("c",),
                    mediators=("m",), colliders=("k",), instruments=("i",))
    assert r.adjustment_set == frozenset({"c"})
    assert r.adjustment_set.isdisjoint({"m", "k", "i"})


def test_causal_roles_is_hashable():
    assert isinstance(hash(CausalRoles(predictor="x", outcome="y")), int)
