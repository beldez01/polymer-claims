"""Bundled datasets for the local real-execution adapters (Phase 2a).

`load_dataset(ref)` resolves a `DataHandle.ref` to the columns of a CSV shipped
alongside this module. Pure stdlib; cached. This is the impure data layer the
real adapters resolve against (the grammar holds only a DataHandle REFERENCE).
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def load_dataset(ref: str) -> dict[str, list[str]]:
    """Return {column_name: [cell, ...]} for the bundled CSV named `<ref>.csv`.
    Raises FileNotFoundError for an unknown ref (the adapter degrades it to a
    node error; it never crashes the run)."""
    path = _DIR / f"{ref}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"no bundled dataset {ref!r} at {path}")
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"dataset {ref!r} is empty")
    cols: dict[str, list[str]] = {k: [] for k in rows[0]}
    for row in rows:
        for k, v in row.items():
            cols[k].append(v)
    return cols
