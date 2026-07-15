"""Independent (leg-B) contract reader for the expression capabilities — audit finding F3.

Leg A of each expression pair (`ExpressionFloorMeanAdapter`, `ExpressionAbsenceMaxAdapter`) reads via
`methyl_adapters._load_betas`, which builds the full beta matrix by a POSITIONAL header↔cell zip and
never cross-checks the TSV against the manifest. If that loader (or its row/column orientation) has a
bug, BOTH legs would inherit it and could still "agree" — inflating the air-gap independence claim.

Leg B reads HERE, via a SEPARATE code path: it extracts only the target `expr::<feature>` row, keys
every value by its SAMPLE NAME (not by position within a shared matrix), and **validates that the TSV
column set equals the manifest col_data sample set** (raising on divergence). So a row-selection,
sample-alignment, or orientation bug in either loader makes the two legs DISAGREE (or one raise), and
no license mints — restoring genuine data-reading independence, not just a distinct statistic.

The only shared code is the trusted contract-resolution infra (`load_contract`/`load_manifest`) — the
analogue of the filesystem; the parsing/extraction that the audit flagged is independent.
Umbrella/impure (stdlib file I/O). NOT re-exported from __init__.
"""
from __future__ import annotations

from pathlib import Path

from polymer_grammar import DataHandle, OperationNode

from .contracts import load_contract, load_manifest


def independent_feature_row(node: OperationNode, feature: str) -> tuple[dict[str, float], dict[str, str]]:
    """Return ({sample_id: value} for `expr::<feature>`, {sample_id: group}). Keyed by sample NAME,
    with a TSV↔manifest sample-set integrity check. Raises on a missing handle/row or a sample
    mismatch. NaN/non-parseable cells are dropped."""
    handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
    if handle is None:
        raise ValueError(f"{node.impl} requires a DataHandle input")
    p = {k: v for k, v in node.params}
    se = load_contract(handle.ref)
    manifest = load_manifest(se)
    group_col = p["group_col"]
    manifest_list = [c["sample_id"] for c in manifest["col_data"]]
    if len(manifest_list) != len(set(manifest_list)):
        raise ValueError("independent-read integrity: duplicate manifest col_data sample ids")
    manifest_samples = set(manifest_list)
    group_of = {c["sample_id"]: c[group_col] for c in manifest["col_data"]}

    row_key = f"expr::{feature}"
    path = Path(se.access_methods[0].access_url)
    with open(path) as fh:
        tsv_samples = fh.readline().rstrip("\n").split("\t")[1:]
        if len(tsv_samples) != len(set(tsv_samples)):
            raise ValueError("independent-read integrity: duplicate TSV sample columns")
        if set(tsv_samples) != manifest_samples:
            raise ValueError(
                "independent-read integrity: contract TSV columns != manifest col_data samples"
            )
        row: dict[str, float] = {}
        for line in fh:
            cells = line.rstrip("\n").split("\t")
            if cells[0] != row_key:
                continue
            # A truncated/ragged row would let `zip` silently DROP a trailing (possibly high) sample,
            # erasing the worst tissue from a safety veto (audit finding 1). Require exact width.
            if len(cells) != len(tsv_samples) + 1:
                raise ValueError(
                    "independent-read integrity: row width != header (truncated/ragged matrix)"
                )
            for name, v in zip(tsv_samples, cells[1:]):
                try:
                    fv = float(v)
                except ValueError:
                    continue
                if fv == fv:                 # drop NaN (NaN != NaN)
                    row[name] = fv
            break
    if not row:
        raise KeyError(f"missing {row_key!r} in contract (independent read)")
    return row, group_of
