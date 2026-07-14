"""The safety-absence e-value for the expression::absence capability (Ch2 GTEx safety atlas).

A one-sample betting e-value on the HEADROOM below a pre-registered ceiling: X_i = (ceiling - expr_i)
rescaled into [0,1], tested against H0: E[headroom] <= margin (reusing evidence._capital_onesample,
the same primitive count_enrichment uses). A large e-value = evidence the target sits at least
`margin` below the ceiling across healthy tissues.

The HARD worst-tissue veto is NOT this e-value — it is the LE criterion on the max-returning adapter
(expression_absence_adapters.ExpressionAbsenceMaxAdapter): a single tissue above the ceiling fails
the criterion regardless of the e-value. This e-value supplies the statistical discrimination that
the headroom is real, not chance. Mirrors expression_floor_evidence (CAP/NULL_GAP pre-registered).

Umbrella/impure (numpy). NOT re-exported from __init__.
"""
from __future__ import annotations

import numpy as np

from .evidence import _SEEDS, _capital_onesample

CAP = 100.0      # rescaling constant: TPM/CAP into [0,1] — pre-registered (matches expression_floor)
NULL_GAP = 0.1   # margin below the ceiling, in [0,1] units — pre-registered


def expression_absence_evalue(
    exprs, *, ceiling: float, cap: float = CAP, margin: float = NULL_GAP
) -> float:
    """betting e-value that healthy-tissue expression sits >= `margin` below `ceiling` (rescaled by
    `cap`). Headroom X_i = clip((ceiling - expr_i)/cap, 0, 1); H0: E[X] <= margin; e >> 1 rejects it
    -> evidence of safety. A tissue at/above the ceiling contributes X=0 (no headroom). Empty -> 0.0.
    """
    x = np.clip((float(ceiling) - np.asarray(list(exprs), dtype=float)) / cap, 0.0, 1.0)
    if x.size == 0:
        return 0.0
    es = [_capital_onesample(x, margin, s) for s in _SEEDS]
    return float(sum(es) / len(es))
