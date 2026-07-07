from polymer_grammar.blame import aggregate_blame
from polymer_grammar.status import PendingReason, Status
from polymer_protocol.sheaf import Obstruction
from polymer_protocol.blame_bridge import blame_set_from_obstruction, blame_verdict_from_obstructions


def _cycle(*ids):
    edges = tuple((ids[i], ids[(i + 1) % len(ids)]) for i in range(len(ids)))
    return Obstruction(claim_ids=tuple(ids), edges=edges, magnitude=1.0)


def test_single_cycle_has_no_local_witness_all_underdetermined():
    # the drift 1->1->1->2 loop of epistemology.md §6: A≈B≈C≈A, every edge fine, cycle open
    bs = blame_set_from_obstruction(_cycle("A", "B", "C"))
    assert bs.contradiction_id == "h1:A|B|C"
    v = aggregate_blame(bs)
    assert v.possibly_blamed == frozenset({"A", "B", "C"})
    assert v.robustly_blamed == frozenset()                     # no local witness
    assert v.underdetermined == frozenset({"A", "B", "C"})      # all PENDING duhem


def test_one_obstruction_is_all_underdetermined_never_robust():
    v = blame_verdict_from_obstructions([_cycle("A", "B", "C")])
    assert v.robustly_blamed == frozenset()
    assert v.underdetermined == frozenset({"A", "B", "C"})


def test_shared_claim_across_two_cycles_is_robustly_blamed():
    # X sits in both frustrated cycles -> the common culprit; the others stay underdetermined
    v = blame_verdict_from_obstructions([_cycle("A", "B", "X"), _cycle("C", "D", "X")])
    assert v.robustly_blamed == frozenset({"X"})
    assert v.possibly_blamed == frozenset({"A", "B", "C", "D", "X"})
    assert v.underdetermined == frozenset({"A", "B", "C", "D"})


def test_no_obstructions_is_empty_verdict():
    v = blame_verdict_from_obstructions([])
    assert v.possibly_blamed == frozenset()
    assert v.robustly_blamed == frozenset()
    assert v.underdetermined == frozenset()


from polymer_grammar.status import RejectionReason
from polymer_protocol.blame_bridge import duhem_statuses_from_obstructions


def test_single_cycle_routes_all_members_to_pending_duhem():
    out = duhem_statuses_from_obstructions([_cycle("A", "B", "C")])
    for cid in ("A", "B", "C"):
        assert out[cid] == (Status.PENDING, PendingReason.DUHEM_UNDERDETERMINED, None)


def test_shared_claim_routes_to_rejected_robustly_blamed():
    out = duhem_statuses_from_obstructions([_cycle("A", "B", "X"), _cycle("C", "D", "X")])
    assert out["X"] == (Status.REJECTED, None, RejectionReason.ROBUSTLY_BLAMED)
    assert out["A"] == (Status.PENDING, PendingReason.DUHEM_UNDERDETERMINED, None)
    assert out["D"] == (Status.PENDING, PendingReason.DUHEM_UNDERDETERMINED, None)
