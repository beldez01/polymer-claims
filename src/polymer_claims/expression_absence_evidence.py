"""The safety-absence e-value for the expression::absence capability (Ch2 GTEx safety atlas).

A one-sample betting e-value on the FRACTIONAL HEADROOM below a pre-registered ceiling:
X_i = clip(1 - expr_i/ceiling, 0, 1) ∈ [0,1], tested against H0: E[headroom] <= margin (reusing
evidence._capital_onesample, the same primitive count_enrichment uses). A large e-value = evidence
the target sits, on average, at least `margin` of the ceiling below it across healthy tissues.

Rescaling by the CEILING (not a fixed TPM cap) is the scale-appropriate choice for a veto: a target
absent across tissues has X≈1 (full headroom → strong e-value) regardless of the ceiling's TPM value,
whereas a fixed cap would compress a realistic ~13 TPM ceiling to ~0.13, barely above the margin.

The HARD worst-tissue veto is NOT this e-value — it is the LE criterion on the max-returning adapter
(expression_absence_adapters.ExpressionAbsenceMaxAdapter): a single tissue above the ceiling fails
the criterion regardless of the e-value. This e-value supplies the statistical discrimination that
the headroom is real, not chance.

Umbrella/impure (numpy). NOT re-exported from __init__.
"""
from __future__ import annotations

import numpy as np

from .evidence import _SEEDS, _capital_onesample

NULL_GAP = 0.1   # margin: mean fractional headroom below the ceiling under H0 — pre-registered


def expression_absence_evalue(exprs, *, ceiling: float, margin: float = NULL_GAP) -> float:
    """betting e-value that healthy-tissue expression sits, on average, at least `margin` of the
    ceiling below it. Fractional headroom X_i = clip(1 - expr_i/ceiling, 0, 1); H0: E[X] <= margin;
    e >> 1 rejects it -> evidence of safety. A tissue at/above the ceiling contributes X=0. A
    non-positive ceiling or an empty atlas -> 0.0 (never fabricated)."""
    ceiling = float(ceiling)
    if ceiling <= 0.0:
        return 0.0
    x = np.clip(1.0 - np.asarray(list(exprs), dtype=float) / ceiling, 0.0, 1.0)
    if x.size == 0:
        return 0.0
    es = [_capital_onesample(x, margin, s) for s in _SEEDS]
    return float(sum(es) / len(es))
