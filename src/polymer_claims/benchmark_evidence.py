from __future__ import annotations
from collections.abc import Sequence
import numpy as np
from .evidence import _C, _grapa_capital


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
