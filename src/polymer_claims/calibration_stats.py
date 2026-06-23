"""Umbrella-side calibration statistics (stdlib-only, deterministic).

A percentile bootstrap for the DEFINITIONAL CI — a more honest interval than the normal-approx
over a small number of batches. Lives umbrella-side (uses `random`) so `protocol/calibration.py`
stays pure/random-free; deterministic via a seeded RNG. NOT re-exported from `__init__` (base
import stays light)."""
from __future__ import annotations

import random
from collections.abc import Sequence


def bootstrap_mean_ci(
    values: Sequence[float], *, n_resamples: int = 2000, seed: int = 0, alpha: float = 0.05
) -> tuple[float | None, float | None]:
    """Deterministic percentile-bootstrap CI for the mean of `values`.

    Resamples the values with replacement using a seeded RNG (reproducible: same values + seed →
    same interval) and returns the (alpha/2, 1-alpha/2) percentiles of the resample means. Returns
    (None, None) for fewer than 2 values — a single point has no bootstrap interval."""
    vals = list(values)
    n = len(vals)
    if n < 2:
        return (None, None)
    rng = random.Random(seed)
    means = [sum(vals[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_resamples)]
    means.sort()
    lo_idx = int((alpha / 2) * n_resamples)
    hi_idx = min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))
    return (means[lo_idx], means[hi_idx])
