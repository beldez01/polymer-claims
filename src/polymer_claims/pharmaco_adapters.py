"""Two INDEPENDENT legs recompute a marker->drug association over the pharmaco SE-Contract.
Leg A (mean difference of within-tissue-split AUCs; feeds the e-value) vs leg B (Hodges-Lehmann
location shift; corroborating air-gap gate). Median-split on the marker's methylation is done
WITHIN each tissue (tissue-adjusted) and is monotone-invariant (the measurement-seam requirement).
Umbrella/impure. NOT re-exported from __init__ (base import stays numpy-free)."""
from __future__ import annotations

import numpy as np
from polymer_grammar import ExecValue, OperationNode

from .methyl_adapters import _load_betas

_IMPL = "pharmaco::assoc"


def _pharmaco_split(node: OperationNode) -> tuple[list[float], list[float]]:
    """(high-meth AUCs, low-meth AUCs), median-split within each tissue on marker methylation,
    pooled across tissues. Drops lines missing either value. Raises on empty groups."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    beta, sample_ids, tissue_of, p = _load_betas(node)  # tissue_of = col_data[group_col]
    marker_row, drug_row = f"meth::{p['marker']}", f"auc::{p['drug']}"
    if marker_row not in beta or drug_row not in beta:
        raise KeyError(f"missing {marker_row!r} or {drug_row!r} in contract")
    meth, auc = beta[marker_row], beta[drug_row]
    hi: list[float] = []
    lo: list[float] = []
    # group lines by tissue
    by_tissue: dict[str, list[str]] = {}
    for s in sample_ids:
        m, a = meth.get(s), auc.get(s)
        if m is None or a is None or np.isnan(m) or np.isnan(a):
            continue
        by_tissue.setdefault(tissue_of[s], []).append(s)
    for _, members in by_tissue.items():
        if len(members) < 2:
            continue
        med = float(np.median([meth[s] for s in members]))
        for s in members:
            (hi if meth[s] > med else lo).append(auc[s])
    if not hi or not lo:
        raise ValueError("empty methylation split group")
    return hi, lo


class PharmacoMeanDiffAdapter:
    """Independent leg A — mean(low-meth AUC) - mean(high-meth AUC). Positive => high-meth
    lines are more sensitive (lower AUC). Feeds the e-value."""

    identity = "pharmaco-meandiff"

    def execute(self, node, upstream, ctx) -> ExecValue:
        hi, lo = _pharmaco_split(node)
        return ExecValue(value=(sum(lo) / len(lo)) - (sum(hi) / len(hi)))


class PharmacoRankAdapter:
    """Independent leg B — Hodges-Lehmann location shift: median of all pairwise (lo_j - hi_i).
    Rank-family, robust to AUC tails; a genuinely different estimator from leg A. Corroborating
    air-gap gate (CapabilityCell.agreement_mode='both_satisfy_criterion'), never feeds the e-value."""

    identity = "pharmaco-rank"

    def execute(self, node, upstream, ctx) -> ExecValue:
        hi, lo = _pharmaco_split(node)
        h = np.asarray(hi, dtype=float)
        lo_arr = np.asarray(lo, dtype=float)
        pairwise = (lo_arr[:, None] - h[None, :]).ravel()
        return ExecValue(value=float(np.median(pairwise)))
