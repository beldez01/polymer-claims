"""Pattern registry — an open, axis-derived catalog (spec §3.1).

A pattern is a typed signature over the statistical-form axes (estimand x adjustment
role x null model x scale) plus its invariance group and at least one *excluded*
application (which pins the relation, closing the Newman hole). The registry is OPEN:
it reports a coverage metric, never closure. `adjusted_effect` merges the legacy
`partial_correlation_with_control` and `model_delta_over_baseline` patterns.
"""
from __future__ import annotations

from pydantic import Field

from .base import _Model


class PatternRef(_Model):
    id: str
    version: str


class Pattern(_Model):
    id: str
    version: str
    estimand: str
    adjustment_role: str | None = None
    null_model: str
    scale: str
    invariance_group: str
    intended_applications: tuple[str, ...]
    # >=1 excluded_application pins the relation (closes the Newman hole)
    excluded_applications: tuple[str, ...] = Field(min_length=1)
    merged_from: tuple[str, ...] = ()
    # neg-whisper ⑤ — a licensed-NEGATIVE pattern: its criterion is a severe test for ABSENCE (the
    # effect is bounded BELOW a threshold). A claim LICENSED under such a pattern is a morphospace
    # FORBIDDEN region (warranted absence at severity) — distinct from PENDING-untested UNOBSERVED.
    # FIREWALL: a licensed negative asserts EARNED WARRANT FOR ABSENCE AT A SEVERITY, never
    # metaphysical impossibility — a licensing status, not a meaning verdict. Default False (a
    # presence pattern), so every existing pattern is unchanged.
    asserts_absence: bool = False


class _Registry:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], Pattern] = {}

    def register(self, pattern: Pattern) -> None:
        self._by_key[(pattern.id, pattern.version)] = pattern

    def get(self, id: str, version: str) -> Pattern:
        return self._by_key[(id, version)]

    def coverage(self) -> dict:
        return {"n_patterns": len(self._by_key), "closed": False}


registry = _Registry()

registry.register(
    Pattern(
        id="adjusted_effect",
        version="v1",
        estimand="adjusted_effect_size",
        adjustment_role="confounder_set",
        null_model="permutation_or_analytic",
        scale="standardized",
        invariance_group="monotone_reparametrization",
        intended_applications=[
            "partial correlation of a predictor with an outcome controlling for confounders",
            "model performance delta over a baseline after adjustment",
        ],
        excluded_applications=[
            "unadjusted bivariate correlation (use simple_correlation)",
            "causal-edge assertion (use the mechanism/causal pattern)",
        ],
        merged_from=["partial_correlation_with_control", "model_delta_over_baseline"],
    )
)

registry.register(
    Pattern(
        id="reported_quantity",
        version="v1",
        estimand="reported_scalar",
        null_model="none_reported_prior",
        scale="ratio_or_interval",
        invariance_group="admissible_unit_transform",
        intended_applications=[
            "a reported point measurement (constant, floor, derived ratio) cited from literature",
        ],
        excluded_applications=[
            "an adjusted or model-relative effect (use adjusted_effect)",
            "a recomputed statistic that passes the licensing gate (use its analysis pattern)",
        ],
    )
)

registry.register(
    Pattern(
        id="mechanistic_law",
        version="v1",
        estimand="qualitative_law",
        null_model="no_law_holds",
        scale="ordinal_relation",
        invariance_group="monotone_reparametrization",
        intended_applications=[
            "a reported mechanistic/relational principle serving as a prior or defeater",
        ],
        excluded_applications=[
            "a quantitative statistical estimand (use reported_quantity or adjusted_effect)",
        ],
    )
)


registry.register(
    Pattern(
        id="bounded_absence",
        version="v1",
        estimand="effect_bounded_below_threshold",
        null_model="effect_at_or_above_threshold",
        scale="standardized",
        invariance_group="monotone_reparametrization",
        intended_applications=[
            "a severe test that an effect is bounded BELOW a threshold — a licensed negative / "
            "morphospace FORBIDDEN region (warranted absence at severity, NOT impossibility)",
        ],
        excluded_applications=[
            "an effect-PRESENCE claim (use adjusted_effect)",
            "an untested/unobserved region (that is PENDING untested, not a licensed negative)",
        ],
        asserts_absence=True,
    )
)


def get_pattern(id: str, version: str) -> Pattern:
    return registry.get(id, version)
