from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.proposition import Direction, NeighborEdge, NeighborEdgeKind, Proposition
from polymer_grammar.status import PendingReason, Status
from polymer_grammar.strength import StrengthVector
from polymer_grammar.revision import Entrench, compare_entrenchment, entails_closure, corpus_entails


# ---- shared test helpers (reused by all later tasks in this file) ----
def _leaf():
    return QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f")


def _sv(severity: float, ean: float) -> StrengthVector:
    # only `severity` and `evidence_against_null` matter for entrenchment; pin the rest mid.
    return StrengthVector(
        magnitude=0.5, uncertainty=0.5, evidence_against_null=ean,
        severity=severity, world_contact=0.5, explanatory_virtue=0.5,
    )


def _prop(desc, direction=Direction.POSITIVE, entails=(), incompat=()):
    neigh = tuple(NeighborEdge(kind=NeighborEdgeKind.ENTAILS, target=t) for t in entails) + \
            tuple(NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH, target=t) for t in incompat)
    return Proposition(direction=direction, estimand="e", descriptor=desc, neighborhood=neigh)


def _claim(cid, prop=None, status=Status.LICENSED, strength=None):
    return Claim(
        id=cid, title=cid, pattern=PatternRef(id="p", version="v1"),
        leaves=(_leaf(),), status=status, strength=strength, conclusion=prop,
    )


# ---- Task 1 tests ----
def test_higher_status_tier_is_more_entrenched():
    a = _claim("a", status=Status.LICENSED)
    # PENDING requires a pending_reason, so build b directly (the _claim helper doesn't set one)
    b = Claim(id="b", title="b", pattern=PatternRef(id="p", version="v1"),
              leaves=(_leaf(),), status=Status.PENDING, pending_reason=PendingReason.UNTESTED)
    assert compare_entrenchment(a, b) == Entrench.GREATER
    assert compare_entrenchment(b, a) == Entrench.LESS


def test_same_tier_strength_dominance():
    a = _claim("a", strength=_sv(0.9, 0.9))
    b = _claim("b", strength=_sv(0.2, 0.2))
    assert compare_entrenchment(a, b) == Entrench.GREATER
    assert compare_entrenchment(b, a) == Entrench.LESS


def test_same_tier_incomparable_strength():
    a = _claim("a", strength=_sv(0.9, 0.1))   # high severity, low evidence
    b = _claim("b", strength=_sv(0.1, 0.9))   # low severity, high evidence
    assert compare_entrenchment(a, b) == Entrench.INCOMPARABLE


def test_strength_present_beats_absent_same_tier():
    a = _claim("a", strength=_sv(0.5, 0.5))
    b = _claim("b", strength=None)
    assert compare_entrenchment(a, b) == Entrench.GREATER
    assert compare_entrenchment(b, a) == Entrench.LESS


def test_equal_entrenchment():
    a = _claim("a", strength=_sv(0.5, 0.5))
    b = _claim("b", strength=_sv(0.5, 0.5))
    assert compare_entrenchment(a, b) == Entrench.EQUAL
    c = _claim("c", strength=None)
    d = _claim("d", strength=None)
    assert compare_entrenchment(c, d) == Entrench.EQUAL


def test_entails_closure_transitive():
    pc = _prop("C")
    pb = _prop("B", entails=(pc.content_hash,))
    pa = _prop("A", entails=(pb.content_hash,))
    claims = [_claim("a", pa), _claim("b", pb), _claim("c", pc)]
    closure = entails_closure({pa.content_hash}, claims)
    assert pa.content_hash in closure  # seeds-included invariant
    assert pb.content_hash in closure and pc.content_hash in closure


def test_corpus_entails_and_no_spurious_reach():
    pc = _prop("C")
    pa = _prop("A", entails=(pc.content_hash,))
    pz = _prop("Z")  # unrelated
    claims = [_claim("a", pa), _claim("c", pc), _claim("z", pz)]
    assert corpus_entails(claims, pc.content_hash) is True
    assert corpus_entails(claims, pz.content_hash) is True       # asserted directly
    pq = _prop("Q")
    assert corpus_entails(claims, pq.content_hash) is False      # not in corpus


def test_conclusion_none_claims_are_inert():
    pa = _prop("A")
    claims = [_claim("a", pa), _claim("n", None)]
    # the None-conclusion claim contributes no edges and no seed hash
    assert corpus_entails(claims, pa.content_hash) is True
