from polymer_protocol.sheaf import SheafEdge, SheafStructure, SheafVertex
from polymer_protocol import frustration_obstructions


def _v(cid):
    return SheafVertex(claim_id=cid, value=0.0)


def _frustrated_triangle():
    # A≡B, B≡C, C⊣A: two agreements + one antagonism = odd signed cycle → frustrated,
    # a contradiction with no local witness. (sign +1 = equivalence, -1 = defeat.)
    return SheafStructure(
        vertices=(_v("A"), _v("B"), _v("C")),
        edges=(
            SheafEdge(kind="equivalence", u="A", v="B", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="B", v="C", weight=1.0, sign=1),
            SheafEdge(kind="defeat", u="C", v="A", weight=1.0, sign=-1),
        ),
    )


def test_frustrated_triangle_is_one_obstruction_over_all_three():
    obs = frustration_obstructions(_frustrated_triangle())
    assert len(obs) == 1
    assert frozenset(obs[0].claim_ids) == frozenset({"A", "B", "C"})


def test_balanced_cycle_has_no_obstruction():
    # all-equivalence triangle: signed-balanced, not frustrated
    s = SheafStructure(
        vertices=(_v("A"), _v("B"), _v("C")),
        edges=(
            SheafEdge(kind="equivalence", u="A", v="B", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="B", v="C", weight=1.0, sign=1),
            SheafEdge(kind="equivalence", u="A", v="C", weight=1.0, sign=1),
        ),
    )
    assert frustration_obstructions(s) == ()
