"""Tests for PredictionVector and score_advantage (Task 2)."""
from __future__ import annotations

import pytest

from polymer_claims.benchmark_evidence import PredictionVector, ScoringError, score_advantage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PREDS_MODEL = (("a", "cat"), ("b", "dog"), ("c", "bird"))
PREDS_BASELINE = (("a", "cat"), ("b", "cat"), ("c", "cat"))
LABELS = {"a": "cat", "b": "dog", "c": "bird"}
ORDER = ["a", "b", "c"]


# ---------------------------------------------------------------------------
# PredictionVector basics
# ---------------------------------------------------------------------------


def test_as_map_returns_dict():
    pv = PredictionVector(PREDS_MODEL)
    m = pv.as_map()
    assert m == {"a": "cat", "b": "dog", "c": "bird"}


def test_as_map_raises_on_duplicate_id():
    pv = PredictionVector((("a", "cat"), ("a", "dog")))
    with pytest.raises(ScoringError):
        pv.as_map()


def test_content_hash_is_sha256_prefixed():
    pv = PredictionVector(PREDS_MODEL)
    assert pv.content_hash.startswith("sha256:")


def test_content_hash_changes_with_different_predictions():
    pv1 = PredictionVector(PREDS_MODEL)
    pv2 = PredictionVector(PREDS_BASELINE)
    assert pv1.content_hash != pv2.content_hash


def test_ref_equals_content_hash():
    pv = PredictionVector(PREDS_MODEL)
    assert pv.ref == pv.content_hash


# ---------------------------------------------------------------------------
# score_advantage — happy path
# ---------------------------------------------------------------------------


def test_score_advantage_basic():
    """3/3 model vs 1/3 baseline → [0, 1, 1]."""
    model = PredictionVector(PREDS_MODEL)
    baseline = PredictionVector(PREDS_BASELINE)
    result = score_advantage(model, baseline, LABELS, ORDER)
    assert result == [0.0, 1.0, 1.0]


# ---------------------------------------------------------------------------
# Order check — each vector's id sequence must equal order exactly
# ---------------------------------------------------------------------------


def test_score_advantage_model_wrong_order_raises():
    """Same ids, different order → ScoringError."""
    model = PredictionVector((("b", "dog"), ("a", "cat"), ("c", "bird")))
    baseline = PredictionVector(PREDS_BASELINE)
    with pytest.raises(ScoringError):
        score_advantage(model, baseline, LABELS, ORDER)


def test_score_advantage_baseline_wrong_order_raises():
    model = PredictionVector(PREDS_MODEL)
    baseline = PredictionVector((("c", "cat"), ("a", "cat"), ("b", "cat")))
    with pytest.raises(ScoringError):
        score_advantage(model, baseline, LABELS, ORDER)


def test_score_advantage_missing_id_raises():
    """Vector with a missing id → ScoringError."""
    model = PredictionVector((("a", "cat"), ("b", "dog")))
    baseline = PredictionVector(PREDS_BASELINE)
    with pytest.raises(ScoringError):
        score_advantage(model, baseline, LABELS, ORDER)


# ---------------------------------------------------------------------------
# Label coverage — set(labels) must == set(order) exactly
# ---------------------------------------------------------------------------


def test_score_advantage_labels_missing_id_raises():
    """Labels dict missing one id from order → ScoringError."""
    model = PredictionVector(PREDS_MODEL)
    baseline = PredictionVector(PREDS_BASELINE)
    sparse_labels = {"a": "cat", "b": "dog"}  # missing "c"
    with pytest.raises(ScoringError):
        score_advantage(model, baseline, sparse_labels, ORDER)


def test_score_advantage_labels_extra_id_raises():
    """Labels dict with an extra id not in order → ScoringError."""
    model = PredictionVector(PREDS_MODEL)
    baseline = PredictionVector(PREDS_BASELINE)
    extra_labels = {"a": "cat", "b": "dog", "c": "bird", "d": "fish"}
    with pytest.raises(ScoringError):
        score_advantage(model, baseline, extra_labels, ORDER)
