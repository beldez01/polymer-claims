from polymer_grammar import DefeatEdge, DefeatEdgeKind, FDRLedger, Status
from polymer_protocol.corpus import Corpus
from polymer_protocol.sheaf import SheafEdge, SheafStructure, SheafVertex, extract_sheaf
from polymer_protocol import frustration_obstructions

from .conftest import _make_quantity_claim as make_quantity_claim


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


def test_structural_sheaf_sees_delicensed_defeats_effective_does_not():
    # Three PENDING (not LICENSED) Quantity-leaf claims with a PROVISIONAL odd defeat cycle
    # A⊣B⊣C⊣A. Provisional defeat edges are inert unless their source is in licensed_ids();
    # since no claim here is LICENSED, the effective sheaf drops all three edges, but the
    # structural sheaf (effective_only=False) ignores the provisional/licensing filter entirely.
    dim = (("mass", 1),)
    a = make_quantity_claim("A", value=1.0, status=Status.PENDING, dim=dim, unit=None)
    b = make_quantity_claim("B", value=1.0, status=Status.PENDING, dim=dim, unit=None)
    c = make_quantity_claim("C", value=1.0, status=Status.PENDING, dim=dim, unit=None)
    defeat_edges = (
        DefeatEdge(source="A", target="B", kind=DefeatEdgeKind.REBUT, provisional=True),
        DefeatEdge(source="B", target="C", kind=DefeatEdgeKind.REBUT, provisional=True),
        DefeatEdge(source="C", target="A", kind=DefeatEdgeKind.REBUT, provisional=True),
    )
    pending_odd_cycle_corpus = Corpus(
        claims=(a, b, c),
        defeat_edges=defeat_edges,
        fdr_ledger=FDRLedger(target_fdr=0.05),
    )

    eff = frustration_obstructions(extract_sheaf(pending_odd_cycle_corpus))                 # effective
    struct = frustration_obstructions(extract_sheaf(pending_odd_cycle_corpus, effective_only=False))
    assert eff == ()                       # no licensed attacker → no effective frustration
    assert struct != ()                    # structural cycle still present
    assert frozenset(struct[0].claim_ids) == frozenset({"A", "B", "C"})
