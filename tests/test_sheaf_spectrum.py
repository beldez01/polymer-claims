# tests/test_sheaf_spectrum.py
import pytest

np = pytest.importorskip("numpy")  # skip cleanly when [embed] absent

from polymer_protocol.sheaf import SheafStructure, SheafVertex, SheafEdge  # noqa: E402
from polymer_claims.sheaf_spectrum import consistency_report  # noqa: E402


def _vert(cid, val):
    return SheafVertex(claim_id=cid, value=val, dimension_sig=(("mass", 1),), unit=None)


def test_agreeing_equivalence_has_zero_energy_and_one_h0():
    s = SheafStructure(vertices=(_vert("a", 2.0), _vert("b", 2.0)),
                       edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=1.0, sign=1),))
    r = consistency_report(s)
    assert r.inconsistency_energy == 0.0
    assert r.h0_dim == 1                       # the two agree -> one consensus dof


def test_disagreeing_equivalence_energy_is_normalized_w_d2():
    s = SheafStructure(vertices=(_vert("a", 1.0), _vert("b", 4.0)),
                       edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=2.0, sign=1),))
    r = consistency_report(s)
    # raw = w*(x_u - x_v)^2 = 2*(1-4)^2 = 18 ; normalized by total weight 2 -> 9
    assert r.inconsistency_energy == pytest.approx(9.0)
    assert r.equivalence_energy == pytest.approx(9.0)
    assert r.defeat_energy == 0.0


def test_defeat_sign_registers_when_values_equal():
    s = SheafStructure(vertices=(_vert("a", 3.0), _vert("b", 3.0)),
                       edges=(SheafEdge(kind="defeat", u="a", v="b", weight=1.0, sign=-1),))
    r = consistency_report(s)
    # raw = w*(x_u + x_v)^2 = (3+3)^2 = 36 ; normalized by 1 -> 36
    assert r.defeat_energy == pytest.approx(36.0)
    assert r.equivalence_energy == 0.0


def test_energy_strictly_decreases_as_values_converge():
    far = consistency_report(SheafStructure(
        vertices=(_vert("a", 0.0), _vert("b", 10.0)),
        edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=1.0, sign=1),)))
    near = consistency_report(SheafStructure(
        vertices=(_vert("a", 4.0), _vert("b", 6.0)),
        edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=1.0, sign=1),)))
    assert near.inconsistency_energy < far.inconsistency_energy


def test_report_is_deterministic():
    s = SheafStructure(vertices=(_vert("a", 1.0), _vert("b", 4.0)),
                       edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=2.0, sign=1),))
    assert consistency_report(s) == consistency_report(s)


def test_sheaf_spectrum_not_re_exported():
    import polymer_claims
    assert not hasattr(polymer_claims, "consistency_report")   # lazy-only, like embedding


# --- H¹ frustration obstruction tests (Task 5) ---

def test_frustrated_cycle_is_localized():
    # A≡B, B≡C, C⊣A : odd defeat count -> frustrated, no global assignment
    s = SheafStructure(
        vertices=(_vert("A", 1.0), _vert("B", 1.0), _vert("C", 1.0)),
        edges=(
            SheafEdge(kind="equivalence", u="A", v="B", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="B", v="C", weight=1.0, sign=1),
            SheafEdge(kind="defeat", u="C", v="A", weight=1.0, sign=-1),
        ),
    )
    r = consistency_report(s)
    assert len(r.h1_obstructions) == 1
    assert set(r.h1_obstructions[0].claim_ids) == {"A", "B", "C"}


def test_balanced_cycle_has_no_obstruction():
    # A≡B, B≡C, C≡A : balanced
    s = SheafStructure(
        vertices=(_vert("A", 1.0), _vert("B", 1.0), _vert("C", 1.0)),
        edges=(
            SheafEdge(kind="equivalence", u="A", v="B", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="B", v="C", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="C", v="A", weight=1.0, sign=1),
        ),
    )
    assert consistency_report(s).h1_obstructions == ()


# --- Folded review finding (2): total energy in defeat test ---

def test_defeat_sign_total_energy():
    s = SheafStructure(vertices=(_vert("a", 3.0), _vert("b", 3.0)),
                       edges=(SheafEdge(kind="defeat", u="a", v="b", weight=1.0, sign=-1),))
    r = consistency_report(s)
    assert r.inconsistency_energy == pytest.approx(36.0)


# --- Folded review finding (3): empty/zero-weight guard ---

def test_no_edges_zero_energy_and_n_h0():
    s = SheafStructure(vertices=(_vert("a", 1.0), _vert("b", 2.0), _vert("c", 3.0)), edges=())
    r = consistency_report(s)
    assert r.inconsistency_energy == 0.0
    assert r.h0_dim == 3


def test_consistency_headline_matches_report_scalars():
    from polymer_claims.sheaf_spectrum import consistency_headline
    s = SheafStructure(vertices=(_vert("a", 1.0), _vert("b", 4.0)),
                       edges=(SheafEdge(kind="equivalence", u="a", v="b", weight=2.0, sign=1),))
    h = consistency_headline(s)
    r = consistency_report(s)
    assert h.inconsistency_energy == r.inconsistency_energy
    assert h.spectral_gap == r.spectral_gap
