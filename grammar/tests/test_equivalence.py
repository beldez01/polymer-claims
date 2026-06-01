import pytest
from pydantic import ValidationError

from polymer_grammar.equivalence import EquivalenceClaim, are_equivalent, equivalence_class
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


# ---------------------------------------------------------------------------
# Resolution tests (Task 3): transitive closure, LICENSED-only, reflexive,
# symmetric
# ---------------------------------------------------------------------------

def _licensed(id_, a, b):
    return EquivalenceClaim(id=id_, left=a, right=b, severity=0.9,
                            status=Status.LICENSED)


def test_equivalence_class_is_transitive_over_licensed_edges():
    eqs = [_licensed("e1", "A", "B"), _licensed("e2", "B", "C")]
    assert equivalence_class("A", eqs) == frozenset({"A", "B", "C"})


def test_reflexive_even_with_no_edges():
    assert equivalence_class("solo", []) == frozenset({"solo"})
    assert are_equivalent("solo", "solo", [])


def test_symmetric():
    eqs = [_licensed("e1", "A", "B")]
    assert are_equivalent("A", "B", eqs)
    assert are_equivalent("B", "A", eqs)


def test_non_licensed_edges_do_not_merge_classes():
    pending = EquivalenceClaim(id="e1", left="A", right="B", severity=0.5,
                               status=Status.PENDING,
                               pending_reason=PendingReason.CONTESTED)
    rejected = EquivalenceClaim(id="e2", left="A", right="C", severity=0.1,
                                status=Status.REJECTED)
    assert equivalence_class("A", [pending, rejected]) == frozenset({"A"})
    assert not are_equivalent("A", "B", [pending, rejected])


def test_disconnected_components_stay_separate():
    eqs = [_licensed("e1", "A", "B"), _licensed("e2", "C", "D")]
    assert equivalence_class("A", eqs) == frozenset({"A", "B"})
    assert not are_equivalent("A", "C", eqs)
    assert not are_equivalent("A", "D", eqs)


# ---------------------------------------------------------------------------
# Task 6: grounded_in rerouting
# NOTE: a local `_eq` already exists above with a **kw signature; this helper
# uses a different name (_make_eq) to avoid collision.
# ---------------------------------------------------------------------------

def _make_eq(id_, left, right, status=Status.LICENSED):
    return EquivalenceClaim(id=id_, left=left, right=right, severity=0.5, status=status)


def test_grounded_in_overrides_licensed_only_stub():
    # edge is LICENSED, so default path links a~b...
    eqs = [_make_eq("e1", "a", "b")]
    assert are_equivalent("a", "b", eqs)  # default (LICENSED) path
    # ...but if the equivalence claim e1 is OUT of the grounded extension, it must NOT link
    assert not are_equivalent("a", "b", eqs, grounded_in=frozenset())
    assert are_equivalent("a", "b", eqs, grounded_in=frozenset({"e1"}))


def test_grounded_in_class_membership():
    eqs = [_make_eq("e1", "a", "b"), _make_eq("e2", "b", "c")]
    # only e1 is IN -> class of a is {a, b}, c excluded
    assert equivalence_class("a", eqs, grounded_in=frozenset({"e1"})) == frozenset({"a", "b"})


def test_grounded_in_overrides_status_entirely():
    # a REJECTED edge whose id is IN the grounded extension still links
    # (grounded_in replaces the status check, not ANDed with it)
    eqs = [_make_eq("e1", "a", "b", status=Status.REJECTED)]
    assert are_equivalent("a", "b", eqs, grounded_in=frozenset({"e1"}))
