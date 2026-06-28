"""§5a literature-shared-cause: did the hypothesis's motivating prior share a cohort with the
test data? If so the "severe test" is closer to confirmation — annotate CONFIRMATORY and cap the
`severity` strength axis (the precise axis the shared-cause leak corrupts). Pure, stdlib only;
imports nothing from polymer_protocol/polymer_claims. First concrete edge of north-star §E's common-cause DAG.
"""
from __future__ import annotations

from enum import Enum

from .strength import StrengthVector

# Tunable: a CONFIRMATORY test is a weak severe test, so its `severity` axis is capped to this
# ceiling (the [0,1] axis is higher-is-better; 0.2 sits in the un-severe band).
CONFIRMATORY_SEVERITY_CEILING: float = 0.2


class SeverityProvenance(str, Enum):
    """Whether the hypothesis source was held out from the test data (a genuine severe test) or
    shares a cohort with it (confirmatory). Orthogonal to IndependenceTier (which is about the
    agreeing legs, not the hypothesis origin)."""

    HELD_OUT = "held_out"
    CONFIRMATORY = "confirmatory"


def shared_cause_overlap(prior_cohorts: tuple[str, ...], test_cohorts: tuple[str, ...]) -> bool:
    """True iff the hypothesis's prior-derivation cohorts intersect the test cohorts (exact ids)."""
    return bool(set(prior_cohorts) & set(test_cohorts))


def severity_provenance_of(
    prior_cohorts: tuple[str, ...], test_cohorts: tuple[str, ...]
) -> SeverityProvenance | None:
    """None when there is no prior-derivation provenance to assess (inert — byte-identical when off).
    Else CONFIRMATORY on overlap, HELD_OUT otherwise (HELD_OUT = no overlap *detected*)."""
    if not prior_cohorts:
        return None
    if shared_cause_overlap(prior_cohorts, test_cohorts):
        return SeverityProvenance.CONFIRMATORY
    return SeverityProvenance.HELD_OUT


def cap_severity_for_confirmatory(strength: StrengthVector) -> StrengthVector:
    """Return a copy with `severity` capped at CONFIRMATORY_SEVERITY_CEILING; all other axes
    untouched. A no-op when the current severity is already <= the ceiling."""
    return strength.model_copy(
        update={"severity": min(strength.severity, CONFIRMATORY_SEVERITY_CEILING)}
    )


# §E (north-star common-cause): Reichenbach screening-off, first concrete form. The graded
# shared-cause overlap between two runs' causal-dependency factor sets. Pairwise overlap below
# SHARED_CAUSE_TAU ⇒ the runs' errors are treated as independent (license may multiply their
# e-values). Operator-asserted factors; derived overlap. Tunable.
SHARED_CAUSE_TAU: float = 0.5


def shared_cause_jaccard(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    """Jaccard overlap |A∩B|/|A∪B| of two factor-tag sets; 0.0 when the union is empty."""
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)
