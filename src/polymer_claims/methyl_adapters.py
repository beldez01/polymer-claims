"""CES-2: region differential-methylation execution over a content-addressed SE Contract.

Two methodologically-independent legs compute the SAME region Δβ = mean(level_b) − mean(level_a) of
the per-sample region-mean betas: a direct group mean-difference and an OLS group coefficient
(numpy lstsq), which equals the mean difference for a two-group design — so they agree (a real
two-implementation air-gap check) yet are genuinely different estimators. Umbrella/impure (file I/O
via load_contract). Grammar + protocol untouched. NOT re-exported from __init__ (keeps base import
numpy-free). See docs/specs/2026-06-12-ces-2-methylation-licensing-design.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from polymer_grammar import DataHandle, ExecValue, OperationNode

from .contracts import load_contract

_IMPL = "methyl::region_delta_beta"


def _region_group_means(node: OperationNode) -> tuple[list[float], list[float]]:
    """Resolve the node's DataHandle to per-sample region-mean betas, split by the two levels.
    Returns (level_a means, level_b means). Raises on bad impl / missing handle / missing probe /
    empty group (the evaluator degrades a raise to a node error)."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
    if handle is None:
        raise ValueError(f"{_IMPL} requires a DataHandle input")
    p = {k: v for k, v in node.params}
    region_probes = [s for s in p["region_probes"].split(",") if s]
    group_col, level_a, level_b = p["group_col"], p["level_a"], p["level_b"]

    se = load_contract(handle.ref)
    betas_path = Path(se.access_methods[0].access_url)
    manifest = json.loads(
        (betas_path.parent / f"{se.contract_uid.split('@')[0]}.json").read_text()
    )
    sample_ids = [c["sample_id"] for c in manifest["col_data"]]
    group_of = {c["sample_id"]: c[group_col] for c in manifest["col_data"]}

    lines = betas_path.read_text().splitlines()
    header = lines[0].split("\t")[1:]
    beta: dict[str, dict[str, float]] = {}
    for ln in lines[1:]:
        cells = ln.split("\t")
        beta[cells[0]] = {sid: float(v) for sid, v in zip(header, cells[1:])}
    for cg in region_probes:
        if cg not in beta:
            raise KeyError(f"region probe {cg!r} not in contract {handle.ref!r}")

    per_sample = {
        sid: sum(beta[cg][sid] for cg in region_probes) / len(region_probes)
        for sid in sample_ids
    }
    a = [per_sample[sid] for sid in sample_ids if group_of[sid] == level_a]
    b = [per_sample[sid] for sid in sample_ids if group_of[sid] == level_b]
    if not a or not b:
        raise ValueError(f"empty group (level_a={len(a)}, level_b={len(b)})")
    return a, b


class RegionMeanDiffAdapter:
    """Independent impl A — direct group mean-difference (level_b − level_a)."""

    identity = "methyl-meandiff-beta"

    def execute(self, node, upstream, ctx) -> ExecValue:
        a, b = _region_group_means(node)
        return ExecValue(value=(sum(b) / len(b)) - (sum(a) / len(a)))


class RegionLmCoefAdapter:
    """Independent impl B — OLS coefficient of region-mean-β on a level_b indicator (numpy lstsq).
    Equals the two-group mean difference exactly, computed by a different estimator."""

    identity = "methyl-lm-coef"

    def execute(self, node, upstream, ctx) -> ExecValue:
        a, b = _region_group_means(node)
        y = np.array(a + b, dtype=float)
        ind = np.array([0.0] * len(a) + [1.0] * len(b))
        X = np.column_stack([np.ones_like(ind), ind])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        return ExecValue(value=float(coef[1]))
