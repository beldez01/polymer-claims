import pytest
from pydantic import ValidationError

from polymer_grammar.equivalence import EquivalenceClaim
from polymer_grammar.status import PendingReason, Status


def _eq(**kw):
    base = dict(id="e1", left="hashA", right="hashB", severity=0.9,
                status=Status.LICENSED)
    base.update(kw)
    return EquivalenceClaim(**base)


def test_equivalence_builds():
    eq = _eq()
    assert eq.left == "hashA" and eq.right == "hashB"


def test_self_equivalence_rejected():
    with pytest.raises(ValidationError):
        _eq(left="same", right="same")


def test_severity_bounds_enforced():
    with pytest.raises(ValidationError):
        _eq(severity=1.5)


def test_pending_requires_reason():
    with pytest.raises(ValidationError):
        _eq(status=Status.PENDING)


def test_pending_reason_only_when_pending():
    with pytest.raises(ValidationError):
        _eq(status=Status.LICENSED, pending_reason=PendingReason.CONTESTED)


def test_pending_with_reason_ok():
    eq = _eq(status=Status.PENDING, pending_reason=PendingReason.CONTESTED)
    assert eq.pending_reason == PendingReason.CONTESTED
