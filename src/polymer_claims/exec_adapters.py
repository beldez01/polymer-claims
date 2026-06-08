"""Phase 2a real-execution adapters: two GENUINELY INDEPENDENT implementations of a
two-group mean difference computed from a bundled dataset.

They share the DATA-ACCESS layer (`load_dataset` + param extraction) but each computes
the statistic with its OWN code, so agreement between them is a real two-implementation
check (the #5 adapter trust registry enforces owner/impl-hash independence on top). A
fully-separate impl or data source (e.g. numpy, or PolymerGenomicsAPI) swaps in later on
the same seam — this slice proves the machinery, not a specific library.

Umbrella/impure ONLY (file I/O via the dataset resolver). Grammar + protocol untouched.
"""
from __future__ import annotations

import statistics

from polymer_grammar import DataHandle, ExecValue, MaterializationContext, OperationNode

from .datasets import load_dataset

_IMPL = "stats::mean_diff"


def _resolve(node: OperationNode) -> tuple[list[float], list[float]]:
    """Resolve the node's DataHandle + params into (group_a values, group_b values).
    Raises on a bad impl / missing handle / missing column / empty group — the evaluator
    degrades the raise to a node error."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
    if handle is None:
        raise ValueError(f"{_IMPL} requires a DataHandle input")
    p = {k: v for k, v in node.params}
    value_col, group_col = p["value_col"], p["group_col"]
    group_a, group_b = p["group_a"], p["group_b"]
    data = load_dataset(handle.ref)
    if value_col not in data or group_col not in data:
        raise KeyError(f"dataset {handle.ref!r} missing column {value_col!r}/{group_col!r}")
    groups = data[group_col]
    values = data[value_col]
    a = [float(v) for v, g in zip(values, groups) if g == group_a]
    b = [float(v) for v, g in zip(values, groups) if g == group_b]
    if not a or not b:
        raise ValueError(f"empty group ({group_a!r}={len(a)}, {group_b!r}={len(b)})")
    return a, b


class StatsPureAdapter:
    """Independent impl A — hand-rolled accumulation (no statistics module)."""

    identity = "stats-pure"

    def execute(
        self, node: OperationNode, upstream: tuple[ExecValue, ...], ctx: MaterializationContext
    ) -> ExecValue:
        a, b = _resolve(node)
        mean_a = sum(a) / len(a)
        mean_b = sum(b) / len(b)
        return ExecValue(value=mean_a - mean_b)


class StatsStdlibAdapter:
    """Independent impl B — uses the stdlib `statistics` module."""

    identity = "stats-stdlib"

    def execute(
        self, node: OperationNode, upstream: tuple[ExecValue, ...], ctx: MaterializationContext
    ) -> ExecValue:
        a, b = _resolve(node)
        return ExecValue(value=statistics.fmean(a) - statistics.fmean(b))
