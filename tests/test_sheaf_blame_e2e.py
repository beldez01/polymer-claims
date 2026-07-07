# tests/test_sheaf_blame_e2e.py
"""Umbrella end-to-end: real numpy frustration detector -> Duhem blame coupling.

Independent second verification route for Tasks 2-4 (polymer_protocol.blame_bridge):
drives the actual SheafStructure/consistency_report detector (polymer_claims.sheaf_spectrum,
numpy/[embed]) instead of hand-built Obstruction fixtures.
"""
import pytest

np = pytest.importorskip("numpy")  # skip cleanly when [embed] absent

from polymer_protocol.sheaf import SheafStructure, SheafVertex, SheafEdge  # noqa: E402
from polymer_claims.sheaf_spectrum import consistency_report  # noqa: E402
from polymer_protocol.blame_bridge import duhem_statuses_from_obstructions  # noqa: E402
from polymer_grammar.status import PendingReason, RejectionReason, Status  # noqa: E402


def _vert(cid, val):
    return SheafVertex(claim_id=cid, value=val, dimension_sig=(("mass", 1),), unit=None)


def test_real_frustrated_cycle_routes_to_pending_duhem():
    # A≡B, B≡C, C⊣A : odd defeat count -> frustrated, no global assignment
    # (same construction as test_sheaf_spectrum.py::test_frustrated_cycle_is_localized)
    s = SheafStructure(
        vertices=(_vert("A", 1.0), _vert("B", 1.0), _vert("C", 1.0)),
        edges=(
            SheafEdge(kind="equivalence", u="A", v="B", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="B", v="C", weight=1.0, sign=1),
            SheafEdge(kind="defeat", u="C", v="A", weight=1.0, sign=-1),
        ),
    )
    report = consistency_report(s)
    assert report.h1_obstructions, "expected at least one H¹ obstruction"

    statuses = duhem_statuses_from_obstructions(report.h1_obstructions)
    assert statuses, "coupling produced no statuses from a real obstruction"
    assert set(statuses) == {"A", "B", "C"}
    for _cid, (status, pending_reason, rejection_reason) in statuses.items():
        assert status == Status.PENDING
        assert pending_reason == PendingReason.DUHEM_UNDERDETERMINED
        assert rejection_reason is None


def test_real_bowtie_shared_vertex_routes_to_robustly_blamed():
    # Two frustrated triangles {A,B,X} and {C,D,X} sharing vertex X (same frustration shape as
    # test_frustrated_cycle_is_localized: two equivalences + one defeat per triangle). X sits in
    # BOTH real detector obstructions -> the robustly-blamed common cause; the rest stay
    # underdetermined (no local witness within their own triangle).
    s = SheafStructure(
        vertices=(
            _vert("A", 1.0), _vert("B", 1.0), _vert("C", 1.0), _vert("D", 1.0), _vert("X", 1.0),
        ),
        edges=(
            SheafEdge(kind="equivalence", u="A", v="B", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="B", v="X", weight=1.0, sign=1),
            SheafEdge(kind="defeat", u="X", v="A", weight=1.0, sign=-1),
            SheafEdge(kind="equivalence", u="C", v="D", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="D", v="X", weight=1.0, sign=1),
            SheafEdge(kind="defeat", u="X", v="C", weight=1.0, sign=-1),
        ),
    )
    report = consistency_report(s)
    assert len(report.h1_obstructions) >= 2
    obstruction_members = {frozenset(o.claim_ids) for o in report.h1_obstructions}
    assert {frozenset({"A", "B", "X"}), frozenset({"C", "D", "X"})} <= obstruction_members

    statuses = duhem_statuses_from_obstructions(report.h1_obstructions)
    assert statuses["X"] == (Status.REJECTED, None, RejectionReason.ROBUSTLY_BLAMED)
    for cid in ("A", "B", "C", "D"):
        assert statuses[cid] == (Status.PENDING, PendingReason.DUHEM_UNDERDETERMINED, None)
