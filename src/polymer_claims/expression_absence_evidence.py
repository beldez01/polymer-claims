"""The safety-absence e-value for the expression::absence capability (Ch2 GTEx safety atlas).

WORST-TISSUE-AWARE by construction (audit): the e-value is 0 unless EVERY tissue clears the ceiling
(worst tissue = max ≤ ceiling). When it does, the severity is a one-sample betting e-value on the
FRACTIONAL HEADROOM X_i = clip(1 - expr_i/ceiling, 0, 1) ∈ [0,1], tested against H0: E[headroom] <=
margin (reusing evidence._capital_onesample, the primitive count_enrichment uses). So the estimand is
"below the ceiling in ALL tissues" — matching the safety claim — not "mean headroom alone".

Why the max gate (not just the mean): without it, a vetoed target with one tissue far above the
ceiling still produced a huge mean-headroom e-value that resolved its FDR test as a discovery and
inflated the e-LOND budget even though the license was withheld. Gating on the (near-deterministic,
per-tissue-median) max makes the e-value refuse to support an unsafe target. Rescaling by the CEILING
(not a fixed TPM cap) keeps a genuinely-safe target's severity strong at realistic ceilings.

Two independent gates enforce safety, defence-in-depth: (1) the LE criterion on the max-returning
adapter (`ExpressionAbsenceMaxAdapter`) is the hard licensing veto; (2) this e-value refuses to
witness safety when the worst tissue exceeds the ceiling. Protocol-side, verify_stage additionally
retracts any non-licensed claim's discovery, so the FDR invariant holds for every capability.

Umbrella/impure (numpy). NOT re-exported from __init__.
"""
from __future__ import annotations

import numpy as np

from .evidence import _SEEDS, _capital_onesample

NULL_GAP = 0.1   # margin: mean fractional headroom below the ceiling under H0 — pre-registered


def expression_absence_evalue(exprs, *, ceiling: float, margin: float = NULL_GAP) -> float:
    """Worst-tissue-aware safety e-value: evidence the target sits at or below `ceiling` in ALL healthy
    tissues. A single tissue strictly above the ceiling REFUTES safety, so the e-value returns 0.0 —
    otherwise a vetoed (unsafe) target's headroom-mean e-value would clear the e-LOND bar and inflate
    the FDR discovery budget even though the max-leg criterion withholds the license (audit finding 1/2).

    On per-tissue median-TPM data the max is (near-)deterministic, so gating on it is the honest
    estimand — "below the ceiling everywhere", not "mean headroom". When the worst tissue clears the
    ceiling, the margin severity is the fractional-headroom betting e-value: X_i = clip(1 - expr_i/
    ceiling, 0, 1), H0: E[X] <= margin. Non-positive ceiling / empty atlas -> 0.0 (never fabricated)."""
    ceiling = float(ceiling)
    if ceiling <= 0.0:
        return 0.0
    arr = np.asarray(list(exprs), dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return 0.0
    if float(arr.max()) > ceiling:      # worst tissue exceeds the ceiling -> not safe -> no support
        return 0.0
    x = np.clip(1.0 - arr / ceiling, 0.0, 1.0)
    es = [_capital_onesample(x, margin, s) for s in _SEEDS]
    return float(sum(es) / len(es))
