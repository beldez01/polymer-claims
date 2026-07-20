"""Domain pattern registration for the sensor::senseability capability (bridge C3).

`sensor_senseability` is a DOMAIN concept (SensorKit RNA-editing sensor geometry — the ordinal
senseability tier of a variant window), so per the expansion doctrine ("domain to the periphery")
it is registered from the umbrella against the shared grammar registry singleton at import — never
written into the pure grammar source. Mirrors `expression_absence_patterns.py`.

The licensable quantity is the ORDINAL geometry tier (unsenseable < engineered < good < ideal),
scored geometry-only (register scan + productivity/CCA + edit distance); thermo/ΔΔG feeds only the
non-gating composite annotation and is out of scope for the licensed tier.
"""
from __future__ import annotations

from polymer_grammar.pattern import Pattern, PatternRef, registry

SENSOR_SENSEABILITY = PatternRef(id="sensor_senseability", version="v1")

registry.register(
    Pattern(
        id="sensor_senseability",
        version="v1",
        estimand="ordinal geometry tier of a variant's RNA-editing sensor window",
        null_model="variant_tier_below_bar",
        scale="ordinal_tier",
        invariance_group="tier_order_preserving_relabeling",
        intended_applications=[
            "the licensable senseability tier of a SNV/junction/whole-target window, "
            "reproduced by two independent geometry classifiers",
        ],
        excluded_applications=[
            "a thermodynamic ΔΔG / composite-annotation score — the licensed tier is geometry-only",
            "a continuous expression summary — that is expression_floor/expression_absence",
        ],
    )
)
