"""earned_strength.py — derive a StrengthVector from a verify result (the 2c reconciliation).

An apparatus-grounded claim EARNS its empirical strength from the computed result instead of
asserting it: evidence_against_null / magnitude scale with the margin by which the agreed
terminal value clears the criterion threshold. The earned evidence then feeds the
selective-inference bar (so a strong real effect legitimately clears the cardinality penalty),
and the oracle tier caps the recorded strength afterward (see protocol/verify.py). Pure: no I/O.
"""
from __future__ import annotations

import math

from polymer_grammar import Comparator, SatisfactionCriterion, StrengthVector

# v1 evidence-curve shape. sat(x)=1-exp(-K*x) maps a non-negative margin ratio into [0,1).
# Calibrated so a true effect that clears the threshold by ~40% of the threshold scale
# (rel_margin 0.4) earns ~0.96 evidence — enough to clear a 2-way BH bar — while a ~10% margin
# earns ~0.55. Tunable; recalibrate against real test statistics (with n) in the 2d arc.
_EVIDENCE_SHAPE_K = 8.0
_EPS = 1e-9

# Theory axes — not earned from data (set by argument); recorded uncapped (v1 fixed defaults).
_SEVERITY = 0.7             # a pre-registered threshold met by real computation is a severe test
_EXPLANATORY_VIRTUE = 0.5   # neutral — no theory argument supplied


def _sat(x: float) -> float:
    """Saturating squash of a non-negative ratio into [0, 1] (reaches 1.0 only when a
    degenerate near-zero threshold scale underflows the exponential; StrengthVector allows 1.0)."""
    if x <= 0.0:
        return 0.0
    return 1.0 - math.exp(-_EVIDENCE_SHAPE_K * x)


def _scale(criterion: SatisfactionCriterion) -> float:
    thr = criterion.threshold
    return max(abs(thr), _EPS) if thr is not None else _EPS


def _rel_margin(value: float, criterion: SatisfactionCriterion) -> float:
    """How far `value` clears the criterion, in threshold units (>=0 when satisfied). EQ/NE/
    WITHIN_TOL and a None threshold have no monotone margin -> 0.0 (floor)."""
    thr = criterion.threshold
    if thr is None:
        return 0.0
    if criterion.comparator in (Comparator.GT, Comparator.GE):
        margin = value - thr
    elif criterion.comparator in (Comparator.LT, Comparator.LE):
        margin = thr - value
    else:
        return 0.0
    return max(margin / _scale(criterion), 0.0)


def earn_strength(
    value: float,
    criterion: SatisfactionCriterion,
    *,
    has_real_data: bool,
    agreement: bool,
) -> StrengthVector:
    """Earn a StrengthVector from a verify result. Goodness empirical axes derive from the margin
    by which `value` clears `criterion` (+ provenance/agreement); theory axes are fixed v1
    defaults. The oracle tier caps the empirical axes downstream (verify.py)."""
    return StrengthVector(
        magnitude=_sat(abs(value) / _scale(criterion)),
        evidence_against_null=_sat(_rel_margin(value, criterion)),
        world_contact=0.9 if has_real_data else 0.3,
        certainty=0.8 if agreement else 0.4,
        severity=_SEVERITY,
        explanatory_virtue=_EXPLANATORY_VIRTUE,
    )
