from __future__ import annotations
from collections.abc import Mapping, Sequence
import numpy as np
from ._hashing import canonical_sha256
from .evidence import _C, _grapa_capital


class ScoringError(ValueError):
    """Raised when prediction vectors or labels fail validation."""


class PredictionVector:
    """Immutable ordered sequence of (example_id, prediction) pairs."""

    def __init__(self, predictions: tuple[tuple[str, str], ...]) -> None:
        self.predictions: tuple[tuple[str, str], ...] = tuple(predictions)

    def as_map(self) -> dict[str, str]:
        """Return a dict of {example_id: prediction}. Raises ScoringError on duplicate ids."""
        result: dict[str, str] = {}
        for eid, pred in self.predictions:
            if eid in result:
                raise ScoringError(f"Duplicate example_id in PredictionVector: {eid!r}")
            result[eid] = pred
        return result

    @property
    def content_hash(self) -> str:
        """Canonical SHA-256 over the ordered (example_id, prediction) pairs."""
        return canonical_sha256([[eid, pred] for eid, pred in self.predictions])

    @property
    def ref(self) -> str:
        """Reference address for this vector (equals content_hash)."""
        return self.content_hash


def score_advantage(
    model: PredictionVector,
    baseline: PredictionVector,
    labels: Mapping[str, str],
    order: Sequence[str],
) -> list[float]:
    """Return Wᵢ = 1(model correct) − 1(baseline correct) in *order*.

    Raises ScoringError if:
    - either vector's id sequence does not equal order exactly
    - set(labels) != set(order)
    - any label lookup fails
    """
    order_tuple = tuple(order)

    # Order check for each vector
    model_ids = tuple(eid for eid, _ in model.predictions)
    if model_ids != order_tuple:
        raise ScoringError(
            f"model PredictionVector id sequence does not match order. "
            f"Got {model_ids}, expected {order_tuple}."
        )
    baseline_ids = tuple(eid for eid, _ in baseline.predictions)
    if baseline_ids != order_tuple:
        raise ScoringError(
            f"baseline PredictionVector id sequence does not match order. "
            f"Got {baseline_ids}, expected {order_tuple}."
        )

    # Label coverage: set(labels) must equal set(order) exactly
    label_ids = set(labels.keys())
    order_ids = set(order_tuple)
    if label_ids != order_ids:
        missing = order_ids - label_ids
        extra = label_ids - order_ids
        raise ScoringError(
            f"Label coverage mismatch. Missing from labels: {missing}. Extra in labels: {extra}."
        )

    # Build maps (raises ScoringError on duplicate ids)
    model_map = model.as_map()
    baseline_map = baseline.as_map()

    weights: list[float] = []
    for eid in order_tuple:
        try:
            true_label = labels[eid]
        except KeyError:
            raise ScoringError(f"Label lookup failed for example_id: {eid!r}")
        model_correct = float(model_map[eid] == true_label)
        baseline_correct = float(baseline_map[eid] == true_label)
        weights.append(model_correct - baseline_correct)
    return weights


def paired_advantage_evalue(w: Sequence[float], *, theta0: float) -> float:
    t = float(theta0)
    if not np.isfinite(t) or not (0.0 <= t < 1.0):
        raise ValueError("theta0 must be finite and in [0, 1)")
    arr = np.asarray(w, dtype=float)
    if arr.size == 0:
        raise ValueError("empty stream")
    if not np.all(np.isfinite(arr)) or np.any(arr < -1.0) or np.any(arr > 1.0):
        raise ValueError("increments must be finite and in [-1, 1]")
    return _grapa_capital(arr - t, _C / (1.0 + abs(t)))
