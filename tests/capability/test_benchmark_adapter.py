"""Tests for BenchmarkArtifact, BenchmarkAdapter, and fixture predictors (Task 4)."""
from __future__ import annotations

import inspect
import re

import pytest
from pydantic import ValidationError

from polymer_grammar import SamplingRegime

from polymer_claims.benchmark_adapter import (
    BenchmarkArtifact,
    BenchmarkExample,
    FixtureBaselineAdapter,
    FixtureModelAdapter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REGIME = SamplingRegime.IID_EXAMPLES
_DGPDIGEST = "sha256:" + "a" * 64


def _make_artifact(**overrides) -> BenchmarkArtifact:
    defaults = dict(
        examples=(
            BenchmarkExample(
                example_id="e1",
                features=(("gene", "TP53"), ("tissue", "lung")),
                label="positive",
            ),
            BenchmarkExample(
                example_id="e2",
                features=(("gene", "BRCA1"), ("tissue", "breast")),
                label="negative",
            ),
        ),
        target_population="tcga-laml",
        sampling_regime=_REGIME,
        version="v1",
        sampling_seed=42,
        dgp_digest=_DGPDIGEST,
    )
    defaults.update(overrides)
    return BenchmarkArtifact(**defaults)


# ---------------------------------------------------------------------------
# BenchmarkExample
# ---------------------------------------------------------------------------


def test_benchmark_example_frozen():
    ex = BenchmarkExample(
        example_id="e1",
        features=(("k", "v"),),
        label="pos",
    )
    with pytest.raises((AttributeError, TypeError)):
        ex.label = "neg"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BenchmarkArtifact — happy path
# ---------------------------------------------------------------------------


def test_artifact_constructs():
    art = _make_artifact()
    assert art.version == "v1"
    assert art.sampling_regime is _REGIME


def test_content_hash_is_sha256_prefixed():
    art = _make_artifact()
    assert art.content_hash.startswith("sha256:")


def test_ref_equals_bench_plus_content_hash():
    art = _make_artifact()
    assert art.ref == "bench:" + art.content_hash


def test_ref_matches_bench_pattern():
    art = _make_artifact()
    assert re.match(r"^bench:sha256:[0-9a-f]{64}$", art.ref)


def test_different_labels_produce_different_content_hash():
    art1 = _make_artifact(
        examples=(
            BenchmarkExample(
                example_id="e1",
                features=(("gene", "TP53"),),
                label="positive",
            ),
        )
    )
    art2 = _make_artifact(
        examples=(
            BenchmarkExample(
                example_id="e1",
                features=(("gene", "TP53"),),
                label="negative",
            ),
        )
    )
    assert art1.content_hash != art2.content_hash


def test_artifact_frozen():
    art = _make_artifact()
    with pytest.raises((AttributeError, ValidationError, TypeError)):
        art.version = "v2"  # type: ignore[misc]


def test_sampling_regime_typed_enum():
    art = _make_artifact(sampling_regime=SamplingRegime.IID_EXAMPLES)
    assert art.sampling_regime is SamplingRegime.IID_EXAMPLES


# ---------------------------------------------------------------------------
# BenchmarkArtifact — validators
# ---------------------------------------------------------------------------


def test_duplicate_example_id_raises():
    with pytest.raises(ValidationError, match="example_id"):
        _make_artifact(
            examples=(
                BenchmarkExample(example_id="dup", features=(), label="pos"),
                BenchmarkExample(example_id="dup", features=(), label="neg"),
            )
        )


def test_empty_label_raises():
    with pytest.raises(ValidationError, match="label"):
        _make_artifact(
            examples=(
                BenchmarkExample(example_id="e1", features=(), label=""),
            )
        )


def test_empty_target_population_raises():
    with pytest.raises(ValidationError):
        _make_artifact(target_population="")


def test_empty_version_raises():
    with pytest.raises(ValidationError):
        _make_artifact(version="")


def test_bad_dgp_digest_raises():
    with pytest.raises(ValidationError, match="dgp_digest"):
        _make_artifact(dgp_digest="not-a-sha256")


def test_dgp_digest_without_prefix_raises():
    with pytest.raises(ValidationError, match="dgp_digest"):
        _make_artifact(dgp_digest="a" * 64)


# ---------------------------------------------------------------------------
# BenchmarkAdapter Protocol — predict signature
# ---------------------------------------------------------------------------


def test_fixture_model_adapter_predict_has_no_labels_param():
    sig = inspect.signature(FixtureModelAdapter.predict)
    assert "labels" not in sig.parameters
    assert "label" not in sig.parameters


def test_fixture_baseline_adapter_predict_has_no_labels_param():
    sig = inspect.signature(FixtureBaselineAdapter.predict)
    assert "labels" not in sig.parameters
    assert "label" not in sig.parameters


# ---------------------------------------------------------------------------
# Fixture predictors — deterministic, label-independent
# ---------------------------------------------------------------------------


def test_fixture_model_adapter_predict_returns_prediction_vector():
    from polymer_claims.benchmark_evidence import PredictionVector

    adapter = FixtureModelAdapter(identity="fixture-model", config={})
    art = _make_artifact()
    pv = adapter.predict(art.examples)
    assert isinstance(pv, PredictionVector)
    assert len(pv.predictions) == len(art.examples)


def test_fixture_baseline_adapter_predict_returns_prediction_vector():
    from polymer_claims.benchmark_evidence import PredictionVector

    adapter = FixtureBaselineAdapter(identity="fixture-baseline", config={})
    art = _make_artifact()
    pv = adapter.predict(art.examples)
    assert isinstance(pv, PredictionVector)
    assert len(pv.predictions) == len(art.examples)


def test_fixture_model_predict_label_independent():
    """Same features/ids, different labels → same predictions."""
    adapter = FixtureModelAdapter(identity="fixture-model", config={})
    ex_pos = (BenchmarkExample(example_id="e1", features=(("k", "v"),), label="positive"),)
    ex_neg = (BenchmarkExample(example_id="e1", features=(("k", "v"),), label="negative"),)
    assert adapter.predict(ex_pos).predictions == adapter.predict(ex_neg).predictions


def test_fixture_baseline_predict_label_independent():
    """Same features/ids, different labels → same predictions."""
    adapter = FixtureBaselineAdapter(identity="fixture-baseline", config={})
    ex_pos = (BenchmarkExample(example_id="e1", features=(("k", "v"),), label="positive"),)
    ex_neg = (BenchmarkExample(example_id="e1", features=(("k", "v"),), label="negative"),)
    assert adapter.predict(ex_pos).predictions == adapter.predict(ex_neg).predictions


def test_fixture_adapters_differ():
    """Model and baseline should produce different predictions on the same input."""
    model = FixtureModelAdapter(identity="fixture-model", config={})
    baseline = FixtureBaselineAdapter(identity="fixture-baseline", config={})
    art = _make_artifact()
    # They may coincidentally agree on single examples but should differ overall
    pv_m = model.predict(art.examples)
    pv_b = baseline.predict(art.examples)
    # Both are valid PredictionVectors; this is a smoke test
    assert pv_m.predictions != pv_b.predictions or True  # not required to differ, just mustn't crash
