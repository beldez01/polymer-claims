import pytest
from pydantic import ValidationError

from polymer_grammar.pattern import Pattern, PatternRef, get_pattern, registry


def test_adjusted_effect_is_seeded_and_merges_two_legacy_patterns():
    p = get_pattern("adjusted_effect", "v1")
    assert p.estimand == "adjusted_effect_size"
    assert "partial_correlation_with_control" in p.merged_from
    assert "model_delta_over_baseline" in p.merged_from


def test_pattern_requires_at_least_one_excluded_application():
    with pytest.raises(ValidationError):
        Pattern(
            id="bad", version="v1", estimand="x", null_model="permutation",
            scale="ratio", invariance_group="affine",
            intended_applications=["something"], excluded_applications=[],
        )


def test_registry_lookup_misses_raise():
    with pytest.raises(KeyError):
        get_pattern("does_not_exist", "v1")


def test_pattern_ref_round_trips():
    ref = PatternRef(id="adjusted_effect", version="v1")
    assert get_pattern(ref.id, ref.version).id == "adjusted_effect"


def test_coverage_metric_reports_registry_size_not_closure():
    assert registry.coverage()["n_patterns"] >= 1
    assert registry.coverage()["closed"] is False
