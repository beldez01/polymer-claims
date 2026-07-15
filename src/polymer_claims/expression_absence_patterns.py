"""Domain pattern registration for the expression-absence (safety-veto) capability.

`expression_absence` is a DOMAIN concept (RNA-seq expression, a GAP-3 ceiling claim), so per the
expansion doctrine ("domain to the periphery") it is registered from the umbrella against the shared
grammar registry singleton at import — never written into the pure grammar source. The inverse of
`expression_floor`: the target's upper summary across healthy tissues must stay BELOW a ceiling.
Mirrors `expression_floor_patterns.py`.
"""
from __future__ import annotations

from polymer_grammar.pattern import Pattern, PatternRef, registry

EXPRESSION_ABSENCE = PatternRef(id="expression_absence", version="v1")

registry.register(
    Pattern(
        id="expression_absence",
        version="v1",
        estimand="worst-tissue expression stays below a ceiling across a healthy atlas",
        null_model="target_expressed_above_ceiling_in_some_tissue",
        scale="continuous_expression",
        invariance_group="monotone_expression_rescaling",
        intended_applications=[
            "on-target/off-tumor safety: a target's max/high-quantile healthy expression vs a ceiling",
        ],
        excluded_applications=[
            "a disease-vs-control over-expression difference — that is expression_floor",
        ],
    )
)
