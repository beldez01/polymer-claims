"""Domain pattern registration for the background-null / fold-enrichment capability.

`background_enrichment` is the honest recast of the TE-family strain. Where the n-DMP pattern's null
is CHANCE (per-probe DMP-rate <= alpha) — almost always rejected when two conditions differ globally —
this pattern's null is a matched genomic BACKGROUND: H0 = "region-class DMP-rate <= matched-background
DMP-rate". A license therefore means the class is ENRICHED for lineage-DMPs above baseline, the claim
the n-DMP gate cannot make (see the TE note's ENGINE LESSON). Registered from the umbrella against the
shared grammar registry singleton at import — never written into the pure grammar source; mirrors
`expression_floor_patterns.py`.
"""
from __future__ import annotations

from polymer_grammar.pattern import Pattern, PatternRef, registry

BACKGROUND_ENRICHMENT = PatternRef(id="background_enrichment", version="v1")

registry.register(
    Pattern(
        id="background_enrichment",
        version="v1",
        estimand="region-class DMP-rate fold-enrichment over a matched genomic background",
        null_model="matched_genomic_background",
        scale="dmp_rate_fraction",
        invariance_group="probe_relabeling",
        intended_applications=[
            "a genomic region-class's per-probe lineage-DMP rate against a matched random-window background",
        ],
        excluded_applications=[
            "more DMPs than chance/noise (per-probe rate > alpha) — that is the n-DMP count pattern, a weaker claim",
        ],
    )
)
