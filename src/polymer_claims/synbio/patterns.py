"""Domain pattern registration for the synthetic-biology arm.

`sense_and_kill` is a DOMAIN concept (synbio-specific), so per the expansion doctrine
("domain to the periphery") it is registered from the umbrella against the shared
grammar registry singleton at import — never written into the pure grammar source.
The analysis-class patterns (`reported_quantity`, `mechanistic_law`) live in the pure
grammar; we re-export their refs here so claims.py has a single import site.
"""
from __future__ import annotations

from polymer_grammar.pattern import Pattern, PatternRef, registry

REPORTED_QUANTITY = PatternRef(id="reported_quantity", version="v1")
MECHANISTIC_LAW = PatternRef(id="mechanistic_law", version="v1")
SENSE_AND_KILL = PatternRef(id="sense_and_kill", version="v1")

registry.register(
    Pattern(
        id="sense_and_kill",
        version="v1",
        estimand="design_composition",
        null_model="no_admissible_design",
        scale="categorical_composition",
        invariance_group="component_relabeling",
        intended_applications=[
            "a (reader, discrimination-topology, actuation, target) therapeutic design tuple",
        ],
        excluded_applications=[
            "surface-antigen CAR targeting with no genotype discrimination (use the antigen pattern)",
            "a bare reported quantity or mechanistic law (use reported_quantity / mechanistic_law)",
        ],
    )
)
