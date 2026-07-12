"""Domain pattern registration for the expression-floor capability.

`expression_floor` is a DOMAIN concept (RNA-seq expression, GAP-3 floor claims), so per the
expansion doctrine ("domain to the periphery") it is registered from the umbrella against the
shared grammar registry singleton at import — never written into the pure grammar source.
Mirrors `src/polymer_claims/synbio/patterns.py`.
"""
from __future__ import annotations

from polymer_grammar.pattern import Pattern, PatternRef, registry

EXPRESSION_FLOOR = PatternRef(id="expression_floor", version="v1")

registry.register(
    Pattern(
        id="expression_floor",
        version="v1",
        estimand="group expression location clears a floor",
        null_model="group_expression_below_floor",
        scale="continuous_expression",
        invariance_group="monotone_expression_rescaling",
        intended_applications=[
            "a single group's expression location (mean/pseudo-median) against a pre-registered TPM floor",
        ],
        excluded_applications=[
            "a between-group difference — that is the e-value, not this pattern",
        ],
    )
)
