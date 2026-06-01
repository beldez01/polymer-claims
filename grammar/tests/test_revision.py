import pytest
from pydantic import ValidationError

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.proposition import Direction, NeighborEdge, NeighborEdgeKind, Proposition
from polymer_grammar.status import PendingReason, Status
from polymer_grammar.strength import StrengthVector
from polymer_grammar.revision import Entrench, compare_entrenchment, entails_closure, corpus_entails, is_consistent, RevisionResult, restore_consistency, expand
from polymer_grammar.defeat import DefeatEdge, DefeatEdgeKind


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


def test_consistent_when_no_incompatibility_resolves():
    pa = _prop("A")
    pb = _prop("B")
    assert is_consistent([_claim("a", pa), _claim("b", pb)]) is True


def test_inconsistent_when_incompatible_pair_present():
    pb = _prop("B", direction=Direction.NEGATIVE)
    pa = _prop("A", incompat=(pb.content_hash,))
    assert is_consistent([_claim("a", pa), _claim("b", pb)]) is False


def test_incompatibility_to_absent_target_is_consistent():
    pb = _prop("B", direction=Direction.NEGATIVE)
    pa = _prop("A", incompat=(pb.content_hash,))
    # only `a` is present; nothing for it to conflict with
    assert is_consistent([_claim("a", pa)]) is True


def test_restore_consistency_retracts_least_entrenched():
    # a (strong) vs b (weak), incompatible -> b robustly retracted, a kept
    pb = _prop("B", direction=Direction.NEGATIVE)
    pa = _prop("A", incompat=(pb.content_hash,))
    a = _claim("a", pa, strength=_sv(0.9, 0.9))
    b = _claim("b", pb, strength=_sv(0.1, 0.1))
    res = restore_consistency([a, b], [])
    assert res.retraction.robustly_retracted == frozenset({"b"})
    assert res.retraction.underdetermined == frozenset()
    assert res.retraction.consistent_core == frozenset({"a"})
    assert {c.id for c in res.claims} == {"a"}


def test_restore_consistency_surfaces_underdetermined_on_incomparable():
    pb = _prop("B", direction=Direction.NEGATIVE)
    pa = _prop("A", incompat=(pb.content_hash,))
    a = _claim("a", pa, strength=_sv(0.9, 0.1))   # incomparable to b
    b = _claim("b", pb, strength=_sv(0.1, 0.9))
    res = restore_consistency([a, b], [])
    assert res.retraction.robustly_retracted == frozenset()
    assert res.retraction.underdetermined == frozenset({"a", "b"})
    assert res.retraction.consistent_core == frozenset()   # neither guaranteed kept


def test_restore_consistency_noop_when_already_consistent():
    a = _claim("a", _prop("A"))
    b = _claim("b", _prop("B"))
    res = restore_consistency([a, b], [])
    assert res.retraction.possibly_retracted == frozenset()
    assert {c.id for c in res.claims} == {"a", "b"}
    assert res.in_set == frozenset({"a", "b"})   # unattacked -> both IN


def test_revision_result_forbids_extra_fields():
    a = _claim("a", _prop("A"))
    restore_consistency([a], [])
    with pytest.raises(ValidationError):
        RevisionResult(claims=(), edges=(), retraction=None, in_set=frozenset(),
                       flipped_in=frozenset(), flipped_out=frozenset(), bogus=1)


def test_restore_consistency_drops_retracted_claims_authored_edges():
    # b is the weak loser of the a/b conflict; an authored edge b->c must NOT keep c OUT
    # after b is retracted (a removed claim's edges die with it — no zombie attack).
    pb = _prop("B", direction=Direction.NEGATIVE)
    pa = _prop("A", incompat=(pb.content_hash,))
    a = _claim("a", pa, strength=_sv(0.9, 0.9))
    b = _claim("b", pb, strength=_sv(0.1, 0.1))
    c = _claim("c", _prop("C"))
    zombie = DefeatEdge(source="b", target="c", kind=DefeatEdgeKind.UNDERMINE)
    res = restore_consistency([a, b, c], [zombie])
    assert "b" in res.retraction.robustly_retracted
    assert res.in_set == frozenset({"a", "c"})                 # c IN: b's edge died with b
    assert all(e.source != "b" and e.target != "b" for e in res.edges)


def test_restore_consistency_multi_conflict_aggregation():
    # a is the weak loser of (a,b) [definite]; (c,d) are incomparable [ambiguous].
    pb = _prop("B", direction=Direction.NEGATIVE)
    pa = _prop("A", incompat=(pb.content_hash,))
    pd = _prop("D", direction=Direction.NEGATIVE)
    pc = _prop("C", incompat=(pd.content_hash,))
    a = _claim("a", pa, strength=_sv(0.1, 0.1))   # weak -> loses to b
    b = _claim("b", pb, strength=_sv(0.9, 0.9))
    c = _claim("c", pc, strength=_sv(0.9, 0.1))   # incomparable to d
    d = _claim("d", pd, strength=_sv(0.1, 0.9))
    res = restore_consistency([a, b, c, d], [])
    assert res.retraction.robustly_retracted == frozenset({"a"})
    assert res.retraction.underdetermined == frozenset({"c", "d"})
    assert res.retraction.consistent_core == frozenset({"b"})


def test_expand_adds_claim_and_recomputes_in_set():
    a = _claim("a", _prop("A"))
    res = expand([a], [], _claim("b", _prop("B")))
    assert {c.id for c in res.claims} == {"a", "b"}
    assert res.retraction is None
    assert res.in_set == frozenset({"a", "b"})        # both unattacked -> IN
    assert res.flipped_in == frozenset({"b"})         # b is newly IN vs prior {a}
    assert res.flipped_out == frozenset()


def test_expand_can_introduce_a_defeat_that_flips_a_claim_out():
    # b rebuts a (mutual incompatibility, equal strength so attacks stand both ways)
    pa = _prop("A")
    pb = _prop("B", direction=Direction.NEGATIVE, incompat=(pa.content_hash,))
    pa2 = _prop("A", incompat=(pb.content_hash,))   # same content as pa, with back-edge
    a = _claim("a", pa2)
    res = expand([a], [], _claim("b", pb))
    # derived mutual rebut, no strength -> attacks stand -> grounded extension empty
    assert res.in_set == frozenset()
    assert "a" in res.flipped_out
