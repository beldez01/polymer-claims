"""Invariance-consistency check (§9) — the FIRST consumer of `Pattern.invariance_group` / `scale`.

measurement-foundation §3.1: a claim earns standing only if its criterion is invariant under the
admissible transformations of its measurement scale; ordinal-treated-as-interval must fail to
type-check. Today `invariance_group`/`scale` ship on `Pattern` (and per measurement space in the B1
registry) but are **never read** by any evaluator (the declared-not-enforced gap). This module reads
them and cross-checks DECLARED coherence between the pattern's scale and the Stevens scale-type of
the measurement space(s) the claim actually reads — catching the "ordinal-as-metric" error (a claim
whose pattern is an ordinal-scale relation reading a metric/ratio space, or vice versa).

**SAFE SLICE — advisory only, NOT wired into the gate.** Making invariance a hard licensing
PRECONDITION (rejecting claims that fail) changes licensing outcomes and is FLAGGED for operator
review (see LOOP-CONTROL / BACKLOG §9). Pure read of grammar + the B1 registry; no Corpus change.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from polymer_grammar import Claim, get_pattern, is_relation

from polymer_claims import measurement_space as ms
from polymer_claims.accumulating_store import contract_uids

_log = logging.getLogger(__name__)


class ScaleClass(str, Enum):
    METRIC = "metric"      # ratio / interval — differences (and, for ratio, ratios) are meaningful
    ORDINAL = "ordinal"    # order only — differences are NOT meaningful
    NOMINAL = "nominal"    # bare categories
    UNKNOWN = "unknown"


# Map the free-form Pattern.scale strings (the 5 in the registry) to a Stevens scale CLASS. Coherence
# is checked at CLASS granularity (metric vs ordinal vs nominal) so ratio-vs-interval ambiguity never
# false-fails, while the load-bearing error (ordinal treated as metric) is caught.
_PATTERN_SCALE_CLASS = {
    "standardized": ScaleClass.METRIC,
    "ratio_or_interval": ScaleClass.METRIC,
    "continuous_expression": ScaleClass.METRIC,
    "dmp_rate_fraction": ScaleClass.METRIC,
    "ordinal_relation": ScaleClass.ORDINAL,
}


def _pattern_scale_class(scale: str) -> ScaleClass:
    return _PATTERN_SCALE_CLASS.get(scale, ScaleClass.UNKNOWN)


def _stevens_class(scale_type: ms.ScaleType) -> ScaleClass:
    if scale_type in (ms.ScaleType.RATIO, ms.ScaleType.INTERVAL):
        return ScaleClass.METRIC
    if scale_type is ms.ScaleType.ORDINAL:
        return ScaleClass.ORDINAL
    if scale_type is ms.ScaleType.NOMINAL:
        return ScaleClass.NOMINAL
    return ScaleClass.UNKNOWN


class InvarianceVerdict(str, Enum):
    COHERENT = "coherent"        # invariance declared AND the pattern's scale-class matches the space's
    UNCHECKED = "unchecked"      # declared, but no registered space to cross-check (or class unknown)
    INCOHERENT = "incoherent"    # the pattern's scale-class conflicts with the space's (e.g. ordinal vs metric)
    UNDECLARED = "undeclared"    # the pattern is missing scale or invariance_group — the precondition is unstated


@dataclass(frozen=True)
class InvarianceReport:
    pattern_scale: str | None
    pattern_invariance_group: str | None
    pattern_scale_class: ScaleClass
    space_scale_classes: tuple[str, ...]  # distinct Stevens classes of the spaces the claim reads
    verdict: InvarianceVerdict


def invariance_report(claim: Claim) -> InvarianceReport:
    """Read the claim's pattern invariance metadata and cross-check it against the measurement
    space(s) it reads (via the B1 registry)."""
    try:
        pat = get_pattern(claim.pattern.id, claim.pattern.version)
    except KeyError:
        return InvarianceReport(None, None, ScaleClass.UNKNOWN, (), InvarianceVerdict.UNDECLARED)
    scale = pat.scale or None
    inv = pat.invariance_group or None
    pclass = _pattern_scale_class(scale or "")
    if not scale or not inv:
        return InvarianceReport(scale, inv, pclass, (), InvarianceVerdict.UNDECLARED)

    space_classes = {
        _stevens_class(sp.scale_type)
        for uid in contract_uids(claim)
        for sp in ms.spaces_for_contract(uid)
    }
    space_classes.discard(ScaleClass.UNKNOWN)
    if not space_classes or pclass is ScaleClass.UNKNOWN:
        verdict = InvarianceVerdict.UNCHECKED
    elif all(sc is pclass for sc in space_classes):
        verdict = InvarianceVerdict.COHERENT
    else:
        verdict = InvarianceVerdict.INCOHERENT
    return InvarianceReport(
        scale, inv, pclass, tuple(sorted(c.value for c in space_classes)), verdict
    )


def invariance_ok(claim: Claim) -> bool:
    """The advisory precondition (NOT wired to the licensing gate): the invariance metadata is
    declared AND not incoherent with the measurement space. UNDECLARED and INCOHERENT fail."""
    return invariance_report(claim).verdict in (
        InvarianceVerdict.COHERENT,
        InvarianceVerdict.UNCHECKED,
    )


def admit_by_invariance(claims: Iterable[Claim]) -> tuple[list[Claim], list[tuple[Claim, InvarianceReport]]]:
    """Umbrella-side LICENSING PRECONDITION (measurement-foundation §3.1): drop any claim whose
    pattern scale-class is INCOHERENT with the measurement space it reads (e.g. an ordinal-scale
    pattern over a ratio/interval space — the ordinal-as-metric error) so it can never LICENSE.

    Conservative + BYTE-IDENTICAL for today's corpora: relations are never invariance-gated, and
    UNDECLARED is LOGGED-not-refused (refusing it would drop relation / unregistered-pattern claims
    and break byte-identity). Only the unambiguous INCOHERENT verdict is refused — and no existing
    licensable claim is INCOHERENT (registered metric patterns read metric spaces; unregistered
    spaces are UNCHECKED). Tighten to also refuse UNDECLARED with the operator once every licensable
    pattern declares its invariance. Returns ``(admitted, refused)``.
    """
    admitted: list[Claim] = []
    refused: list[tuple[Claim, InvarianceReport]] = []
    for c in claims:
        if is_relation(c):
            admitted.append(c)
            continue
        rep = invariance_report(c)
        if rep.verdict is InvarianceVerdict.INCOHERENT:
            _log.warning(
                "invariance precondition: refusing %s — pattern scale-class %s conflicts with "
                "measurement space class(es) %s",
                c.id, rep.pattern_scale_class.value, rep.space_scale_classes,
            )
            refused.append((c, rep))
            continue
        if rep.verdict is InvarianceVerdict.UNDECLARED:
            _log.info("invariance precondition: %s UNDECLARED (admitted; pattern lacks scale/invariance)", c.id)
        admitted.append(c)
    return admitted, refused
