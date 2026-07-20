"""sensor::senseability — Leg B: an INDEPENDENT reimplementation of SensorKit's
senseability tier classifier.

The bridge (`BRIDGE-SENSORKIT-CLAIMS-SPEC.md` §4) licenses at `REPRODUCED` only if a
second, genuinely independent implementation of the tier agrees with SensorKit (Leg A).
The license is on the **ordinal geometry tier** (`classify_variant`), which is
geometry-only (register scan + productivity/CCA + edit distance; thermo/ΔΔG feeds only
the non-gating composite annotation).

This module is that second implementation. It is written against the frozen public
contract (SensorKit `GEOMETRY-CONTRACT.md` v1) — NOT by importing SensorKit — with a
deliberately separate code path (single-pass best-tracking over direct character
indices, no Register objects), so a bug in one classifier cannot corrupt both. It has
its own owner and `implementation_hash`. If this ever imports SensorKit's internals,
the agreement is theatre and the standing collapses to single-source EVIDENCE_LICENSED.
"""
from __future__ import annotations

# Ordinal encoding of the licensable tier (spec §3): higher = more senseable.
TIER_ORDINAL = {"unsenseable": 0, "engineered": 1, "good": 2, "ideal": 3}


def _editability(b1: str, b2: str, b3: str) -> float:
    """Independent productivity per contract §1: the target triplet ``b1 b2 b3`` whose
    middle base pairs opposite the sensor's edited A. 0 unless ``b2 == 'C'``; the 5'-GA
    trap (``b3 == 'C'``) caps at 0.15; otherwise asymmetric flank bonuses."""
    if b2 != "C":
        return 0.0
    if b3 == "C":
        return 0.15
    val = 0.4
    if b3 == "A":
        val += 0.4
    if b1 == "C":
        val += 0.2
    return round(val, 4)


def _adjacency_penalty(distance: int) -> float:
    return max(0.1, 0.6 - 0.1 * distance)


def reimpl_classify_variant(
    window_wt: str, window_mut: str, var_index: int, max_dist: int = 2
) -> str:
    """Independent tier: scan every candidate edit position within ``max_dist`` of the
    variant, keep the one with the highest discrimination (contract §2 tiebreak
    ``(discrimination, -distance, mut_productivity, -edit_index)``), and tier it by
    distance + mutant productivity (contract §3). Returns one of TIER_ORDINAL's keys.
    """
    wt = window_wt.upper().replace("T", "U")
    mut = window_mut.upper().replace("T", "U")
    n = len(mut)

    best_key = None            # (discrimination, -distance, mut_prod, -edit_index)
    best_distance = None
    best_mut_prod = None

    for e in range(1, n - 1):
        distance = abs(var_index - e)
        if distance > max_dist:
            continue
        mut_prod = _editability(mut[e - 1], mut[e], mut[e + 1])
        if mut_prod == 0.0:
            continue
        wt_prod = _editability(wt[e - 1], wt[e], wt[e + 1])
        if distance <= 1:
            discrimination = mut_prod - wt_prod
        else:
            discrimination = mut_prod * _adjacency_penalty(distance)
        if discrimination <= 0:
            continue
        key = (discrimination, -distance, mut_prod, -e)
        if best_key is None or key > best_key:
            best_key = key
            best_distance = distance
            best_mut_prod = mut_prod

    if best_key is None:
        return "unsenseable"
    if best_distance == 0:
        return "ideal" if best_mut_prod == 1.0 else "good"
    return "engineered"


def reimpl_tier_ordinal(
    window_wt: str, window_mut: str, var_index: int, max_dist: int = 2
) -> int:
    """The tier as its licensable ordinal integer (the gate quantity, spec §3)."""
    return TIER_ORDINAL[reimpl_classify_variant(window_wt, window_mut, var_index, max_dist)]
