"""The Phase 1 probe harness — build the five claims and emit the structured probe report.

`probe_report()` is the machine-readable companion to
`docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md`. The gap list mirrors that
document; the two general-class gaps (context-conditioning, interval values) are the headline
finds, since they compound across every field (the expansion doctrine's intended payoff).
"""
from __future__ import annotations

from polymer_grammar.claim import Claim

from .claims import (
    adar_dynamic_range_claim,
    affinity_discrimination_law_claim,
    car_threshold_claim,
    endosomal_escape_claim,
    mismatch_energy_claim,
)

_FACTORIES = (
    mismatch_energy_claim,
    adar_dynamic_range_claim,
    car_threshold_claim,
    endosomal_escape_claim,
    affinity_discrimination_law_claim,
)

# Mirrors the gap report. `expansion_class`: general (core primitive) / analysis (pattern) /
# wiring (no IR change). See docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md.
_GAPS: tuple[dict[str, str], ...] = (
    {"id": "GAP-1", "expansion_class": "analysis",
     "summary": "no home pattern for a bare reported quantity or a mechanistic law"},
    {"id": "GAP-2", "expansion_class": "general",
     "summary": "QuantityLeaf has no context-conditioning field"},
    {"id": "GAP-3", "expansion_class": "general",
     "summary": "no interval/range value (value + symmetric uncertainty is insufficient)"},
    {"id": "GAP-4", "expansion_class": "wiring",
     "summary": "reported-stratum defeaters must author only provisional edges"},
)


def build_all() -> list[Claim]:
    """Construct all five probe claims. Construction is validation: an ill-formed claim raises."""
    return [factory() for factory in _FACTORIES]


def probe_report() -> dict:
    """Per-claim leaf kind / validated / status / source, plus the classified gap list."""
    claims = build_all()
    entries = []
    for c in claims:
        leaf = c.leaves[0]
        entries.append(
            {
                "id": c.id,
                "leaf_kind": leaf.kind,
                "validated": True,  # construction succeeded => the grammar accepted it
                "status": c.status.value,
                "source": c.provenance.method if c.provenance else None,
            }
        )
    return {"claims": entries, "gaps": [dict(g) for g in _GAPS]}
