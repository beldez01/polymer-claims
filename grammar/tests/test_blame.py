import pytest
from pydantic import ValidationError

from polymer_grammar.blame import (
    BlameAssignment, BlameSet, BlameVerdict, aggregate_blame, duhem_status,
)
from polymer_grammar.status import PendingReason, Status


def test_empty_assignment_rejected():
    with pytest.raises(ValidationError):
        BlameAssignment(targets=())


def test_empty_blameset_rejected():
    with pytest.raises(ValidationError):
        BlameSet(contradiction_id="k", assignments=())


def test_single_assignment_is_fully_robust():
    bs = BlameSet(contradiction_id="k",
                  assignments=(BlameAssignment(targets=("c1", "c2")),))
    v = aggregate_blame(bs)
    assert v.robustly_blamed == frozenset({"c1", "c2"})
    assert v.underdetermined == frozenset()
    assert v.possibly_blamed == frozenset({"c1", "c2"})


def test_overlapping_assignments_split_robust_vs_underdetermined():
    bs = BlameSet(contradiction_id="k", assignments=(
        BlameAssignment(targets=("c1", "c2")),
        BlameAssignment(targets=("c1", "aux:assumptionA")),
    ))
    v = aggregate_blame(bs)
    assert v.robustly_blamed == frozenset({"c1"})                 # in every repair
    assert v.underdetermined == frozenset({"c2", "aux:assumptionA"})
    assert v.possibly_blamed == frozenset({"c1", "c2", "aux:assumptionA"})


def test_disjoint_assignments_all_underdetermined():
    bs = BlameSet(contradiction_id="k", assignments=(
        BlameAssignment(targets=("c1",)),
        BlameAssignment(targets=("c2",)),
    ))
    v = aggregate_blame(bs)
    assert v.robustly_blamed == frozenset()
    assert v.underdetermined == frozenset({"c1", "c2"})
    assert v.possibly_blamed == frozenset({"c1", "c2"})


def test_duhem_status_maps_underdetermined_and_robust():
    v = BlameVerdict(
        robustly_blamed=frozenset({"c1"}),
        possibly_blamed=frozenset({"c1", "c2"}),
        underdetermined=frozenset({"c2"}),
    )
    assert duhem_status("c2", v) == (Status.PENDING, PendingReason.DUHEM_UNDERDETERMINED)
    assert duhem_status("c1", v) == (Status.REJECTED, None)
    assert duhem_status("c3", v) is None
