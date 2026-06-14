from __future__ import annotations

import pytest

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    PatternRef,
    PendingReason,
    RejectionReason,
    Status,
)


def _claim(status, **extra):
    return Claim(
        id="x", title="x", pattern=PatternRef(id="p", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="t"),), status=status, **extra,
    )


def test_rejection_reason_values():
    assert {r.value for r in RejectionReason} == {
        "defeat_grounded_out", "refuted", "robustly_blamed",
    }


def test_pending_reason_reinstated_exists():
    assert PendingReason.REINSTATED.value == "reinstated"


def test_rejected_claim_accepts_rejection_reason():
    c = _claim(Status.REJECTED, rejection_reason=RejectionReason.DEFEAT_GROUNDED_OUT)
    assert c.rejection_reason is RejectionReason.DEFEAT_GROUNDED_OUT


def test_rejected_claim_allows_none_reason_backcompat():
    c = _claim(Status.REJECTED)
    assert c.rejection_reason is None


def test_non_rejected_claim_rejects_rejection_reason():
    with pytest.raises(ValueError, match="only valid when status=REJECTED"):
        _claim(Status.CONJECTURED, rejection_reason=RejectionReason.REFUTED)


def test_pending_with_reinstated_reason_validates():
    c = _claim(Status.PENDING, pending_reason=PendingReason.REINSTATED)
    assert c.pending_reason is PendingReason.REINSTATED
