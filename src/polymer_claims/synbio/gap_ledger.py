"""Aggregate manifest schema_fit gaps into the fixed, deduplicated gap list (GAP-N).

Dedup on a controlled `gap_kind` tag so the same strain recorded (and worded) many ways collapses to
one canonical, stably-numbered entry. `CANONICAL_GAP_KINDS` is the source of truth for kind -> number;
a recognized kind always gets its canonical GAP-N. Untagged gaps fall back to the legacy prose key and
number sequentially from a base that never collides with a canonical number.
"""
from __future__ import annotations

from dataclasses import dataclass

from .manifest import ManifestEntry

# Controlled vocabulary: gap_kind -> stable canonical GAP-N. GAP-5/6/9/10/12 do not appear — they were
# the interval/range/floor/bound family, now unified under `interval-bound` (GAP-3, resolved 2026-07-12).
CANONICAL_GAP_KINDS: dict[str, str] = {
    "reported-quantity-pattern":     "GAP-1",
    "context-conditioning":          "GAP-2",
    "interval-bound":                "GAP-3",
    "reported-defeater-provisional": "GAP-4",
    "analytic-basis":                "GAP-7",
    "gene-locus-context":            "GAP-8",
    "stratification":                "GAP-11",
    "endpoint-type":                 "GAP-13",
    "composite-quantity":            "GAP-14",
    "categorical-mapping":           "GAP-15",
}


@dataclass(frozen=True)
class GapRecord:
    id: str
    constraint: str
    current_ir_behavior: str | None
    candidate_resolution: str | None
    expansion_class: str | None
    purity_cost: str | None
    gap_kind: str | None


def _prose_key(sf) -> tuple[str, str]:
    return ((sf.expansion_class or "").strip().lower(),
            (sf.constraint or "").strip().lower())


def aggregate_gaps(entries: list[ManifestEntry], start_index: int = 5) -> list[GapRecord]:
    canonical_nums = [int(v.split("-", 1)[1]) for v in CANONICAL_GAP_KINDS.values()]
    next_free = max(max(canonical_nums, default=0), start_index - 1) + 1
    seen: dict[object, GapRecord] = {}
    for e in entries:
        sf = e.schema_fit
        if sf.status != "gap":
            continue
        kind = (sf.gap_kind or "").strip().lower()
        key: object = kind or _prose_key(sf)
        if key in seen:
            continue
        gap_id = CANONICAL_GAP_KINDS.get(kind)
        if gap_id is None:
            gap_id = f"GAP-{next_free}"
            next_free += 1
        seen[key] = GapRecord(
            id=gap_id,
            constraint=sf.constraint or "",
            current_ir_behavior=sf.current_ir_behavior,
            candidate_resolution=sf.candidate_resolution,
            expansion_class=sf.expansion_class,
            purity_cost=sf.purity_cost,
            gap_kind=sf.gap_kind,
        )
    return list(seen.values())
