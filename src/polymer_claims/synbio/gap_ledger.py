"""Aggregate manifest schema_fit gaps into the fixed, deduplicated gap list (GAP-N).

Dedup by normalized (expansion_class, constraint) so the same strain recorded on many
manifest entries collapses to one canonical, numbered entry. Numbering continues from the
existing gap-log (GAP-1..4 already used), default start_index=5.
"""
from __future__ import annotations

from dataclasses import dataclass

from .manifest import ManifestEntry


@dataclass(frozen=True)
class GapRecord:
    id: str
    constraint: str
    current_ir_behavior: str | None
    candidate_resolution: str | None
    expansion_class: str | None
    purity_cost: str | None


def _key(sf) -> tuple[str, str]:
    return ((sf.expansion_class or "").strip().lower(),
            (sf.constraint or "").strip().lower())


def aggregate_gaps(entries: list[ManifestEntry], start_index: int = 5) -> list[GapRecord]:
    seen: dict[tuple[str, str], GapRecord] = {}
    n = start_index
    for e in entries:
        sf = e.schema_fit
        if sf.status != "gap":
            continue
        k = _key(sf)
        if k in seen:
            continue
        seen[k] = GapRecord(
            id=f"GAP-{n}",
            constraint=sf.constraint or "",
            current_ir_behavior=sf.current_ir_behavior,
            candidate_resolution=sf.candidate_resolution,
            expansion_class=sf.expansion_class,
            purity_cost=sf.purity_cost,
        )
        n += 1
    return list(seen.values())
