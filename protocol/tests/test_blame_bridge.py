from polymer_grammar.blame import aggregate_blame
from polymer_grammar.status import PendingReason, Status
from polymer_protocol.sheaf import Obstruction
from polymer_protocol.blame_bridge import blame_set_from_obstruction


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
