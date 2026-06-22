"""Shared minimal Claim builders for calibration tests.

Pattern mirrored from conftest.make_claim + _licensing() in test_cycle.py:
  - licensed: status=LICENSED + a valid Licensing block (SEVERE_TEST route, one SATISFIED materialization)
  - pending:  status=PENDING + pending_reason=UNTESTED (the conftest default)
  - rejected: status=REJECTED + rejection_reason=<caller-supplied>
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    LicenseRoute,
    Licensing,
    MaterializationContext,
    PatternRef,
    PendingReason,
    RejectionReason,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
    Status,
)

_PATTERN = PatternRef(id="adjusted_effect", version="v1")


def _licensing_block() -> Licensing:
    """Minimal valid Licensing — mirrors _licensing() in test_cycle.py."""
    mat = MaterializationContext(id="m1", api_version="v1", data_version="v1")
    sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=mat)
    return Licensing(
        route=LicenseRoute.SEVERE_TEST,
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
        rivals_considered=(),
        satisfactions=(sat,),
    )


def _base(cid: str, status: Status, **kw) -> Claim:
    """Smallest claim that passes Claim validators for the given status."""
    return Claim(
        id=cid,
        title=f"claim {cid}",
        pattern=_PATTERN,
        leaves=(CategoricalLeaf(ontology_term=f"term-{cid}"),),
        status=status,
        **kw,
    )


def licensed_claim(cid: str) -> Claim:
    """A LICENSED claim with a valid licensing block."""
    return _base(cid, Status.LICENSED, licensing=_licensing_block())


def pending_claim(cid: str) -> Claim:
    """A PENDING claim (UNTESTED, no plan)."""
    return _base(cid, Status.PENDING, pending_reason=PendingReason.UNTESTED)


def rejected_claim(cid: str, reason: RejectionReason) -> Claim:
    """A REJECTED claim with the given rejection_reason."""
    return _base(cid, Status.REJECTED, rejection_reason=reason)
