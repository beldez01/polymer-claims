import pytest
from pydantic import ValidationError

from polymer_grammar.claim import Claim
from polymer_grammar.defeat import (
    ATTACK_KINDS,
    DefeatEdge,
    DefeatEdgeKind,
    derived_rebut_edges,
    effective_defeats,
    grounded_extension,
    undermine_edges_from_failed_satisfactions,
)
from polymer_grammar.licensing import MaterializationContext, Satisfaction, SatisfactionVerdict
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.proposition import Direction, NeighborEdge, NeighborEdgeKind, Proposition
from polymer_grammar.status import PendingReason, Status
from polymer_grammar.strength import StrengthVector


def test_edge_kinds_are_five_attacks_plus_support():
    assert {k.value for k in DefeatEdgeKind} == {
        "undermine", "undercut", "rebut", "reclassify", "reinterpret", "evidence_for",
    }
    assert DefeatEdgeKind.EVIDENCE_FOR not in ATTACK_KINDS
    assert len(ATTACK_KINDS) == 5


def test_edge_is_frozen_and_hashable():
    e = DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT)
    assert isinstance(hash(e), int)
    with pytest.raises(ValidationError):
        DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT, bogus=1)


def test_self_loop_rejected():
    with pytest.raises(ValidationError):
        DefeatEdge(source="a", target="a", kind=DefeatEdgeKind.UNDERMINE)


def _sv(x: float) -> StrengthVector:
    # uniform vector at level x on all six axes
    return StrengthVector(
        magnitude=x, uncertainty=x, evidence_against_null=x,
        severity=x, world_contact=x, explanatory_virtue=x,
    )


def test_attack_filtered_when_target_dominates_source():
    edges = [DefeatEdge(source="weak", target="strong", kind=DefeatEdgeKind.REBUT)]
    strength = {"weak": _sv(0.2), "strong": _sv(0.9)}
    # target (strong) dominates source (weak) -> attack does NOT defeat
    assert effective_defeats(edges, strength) == frozenset()


def test_attack_filtered_when_strengths_equal():
    edges = [DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT)]
    s = {"a": _sv(0.5), "b": _sv(0.5)}
    # equal vectors: target is at-least-as-strong (>=) -> attack does NOT defeat
    assert effective_defeats(edges, s) == frozenset()


def test_attack_stands_when_source_dominates_target():
    edges = [DefeatEdge(source="strong", target="weak", kind=DefeatEdgeKind.REBUT)]
    strength = {"strong": _sv(0.9), "weak": _sv(0.2)}
    assert effective_defeats(edges, strength) == frozenset({("strong", "weak")})


def test_attack_stands_when_incomparable():
    # incomparable: a higher on some axis, b higher on another
    a = StrengthVector(magnitude=0.9, uncertainty=0.1, evidence_against_null=0.5,
                       severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    b = StrengthVector(magnitude=0.1, uncertainty=0.9, evidence_against_null=0.5,
                       severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    edges = [DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.UNDERCUT)]
    assert effective_defeats(edges, {"a": a, "b": b}) == frozenset({("a", "b")})


def test_attack_stands_when_strength_missing():
    a = StrengthVector(magnitude=0.9, uncertainty=0.1, evidence_against_null=0.5,
                       severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    b = StrengthVector(magnitude=0.1, uncertainty=0.9, evidence_against_null=0.5,
                       severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    edges = [DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.UNDERCUT)]
    # missing strength (empty mapping) -> attack stands
    assert effective_defeats(edges, {}) == frozenset({("a", "b")})
    # asymmetric None: either side absent -> attack stands
    assert effective_defeats(edges, {"a": a, "b": None}) == frozenset({("a", "b")})
    assert effective_defeats(edges, {"a": None, "b": b}) == frozenset({("a", "b")})


def test_evidence_for_is_never_a_defeat():
    edges = [DefeatEdge(source="x", target="y", kind=DefeatEdgeKind.EVIDENCE_FOR)]
    assert effective_defeats(edges, {"x": _sv(0.1), "y": _sv(0.9)}) == frozenset()


def test_unattacked_claims_are_in():
    assert grounded_extension(["a", "b"], [], {}) == frozenset({"a", "b"})


def test_mutual_attack_both_out_when_attacks_stand():
    # a <-> b mutual attack; no strength -> no value filter, both attacks stand
    # -> classic Dung mutual attack: grounded extension is empty.
    edges = [
        DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT),
    ]
    assert grounded_extension(["a", "b"], edges, {}) == frozenset()


def test_reinstatement():
    # c -> a -> b, all attacks stand. grounded = {c, b}: a is OUT, so b is reinstated.
    edges = [
        DefeatEdge(source="c", target="a", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="a", target="b", kind=DefeatEdgeKind.REBUT),
    ]
    assert grounded_extension(["a", "b", "c"], edges, {}) == frozenset({"c", "b"})


def test_value_filter_breaks_symmetry():
    # mutual attack, but 'strong' dominates 'weak': weak's attack on strong is filtered,
    # strong's attack on weak stands -> grounded = {strong}.
    edges = [
        DefeatEdge(source="weak", target="strong", kind=DefeatEdgeKind.REBUT),
        DefeatEdge(source="strong", target="weak", kind=DefeatEdgeKind.REBUT),
    ]
    strength = {"weak": _sv(0.2), "strong": _sv(0.9)}
    assert grounded_extension(["weak", "strong"], edges, strength) == frozenset({"strong"})


def test_edge_endpoints_not_in_claim_ids_still_participate():
    # synthetic attacker 'r' (not in claim_ids), no strength -> unattacked, IN, defeats 'a'
    edges = [DefeatEdge(source="r", target="a", kind=DefeatEdgeKind.UNDERMINE)]
    ext = grounded_extension(["a"], edges, {})
    assert "a" not in ext
    assert "r" in ext


def _leaf():
    return QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f")


def _claim(cid, prop, status=Status.LICENSED):
    return Claim(
        id=cid, title=cid, pattern=PatternRef(id="p", version="v1"),
        leaves=(_leaf(),), status=status, conclusion=prop,
    )


def test_derived_rebut_between_incompatible_licensed_claims():
    # prop_b is what prop_a is incompatible_with (by content_hash)
    prop_b = Proposition(direction=Direction.NEGATIVE, estimand="e", descriptor="d-neg")
    prop_a = Proposition(
        direction=Direction.POSITIVE, estimand="e", descriptor="d-pos",
        neighborhood=(NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH,
                                   target=prop_b.content_hash),),
    )
    a = _claim("a", prop_a)
    b = _claim("b", prop_b)
    edges = derived_rebut_edges([a, b])
    pairs = {(e.source, e.target, e.kind) for e in edges}
    assert ("a", "b", DefeatEdgeKind.REBUT) in pairs
    assert ("b", "a", DefeatEdgeKind.REBUT) in pairs


def test_no_derived_rebut_for_non_licensed_or_unmatched():
    prop_b = Proposition(direction=Direction.NEGATIVE, estimand="e", descriptor="d-neg")
    prop_a = Proposition(
        direction=Direction.POSITIVE, estimand="e", descriptor="d-pos",
        neighborhood=(NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH,
                                   target=prop_b.content_hash),),
    )
    # `a` is PENDING (not LICENSED) -> excluded from derived rebut; needs a pending_reason
    a = Claim(
        id="a", title="a", pattern=PatternRef(id="p", version="v1"),
        leaves=(_leaf(),), status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED, conclusion=prop_a,
    )
    b = _claim("b", prop_b)
    assert derived_rebut_edges([a, b]) == ()


def test_no_derived_rebut_when_incompatible_target_has_no_matching_claim():
    # LICENSED claim declares incompatible_with, but no other claim holds that conclusion.
    prop_b = Proposition(direction=Direction.NEGATIVE, estimand="e", descriptor="absent")
    prop_a = Proposition(
        direction=Direction.POSITIVE, estimand="e", descriptor="d-pos",
        neighborhood=(NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH,
                                   target=prop_b.content_hash),),
    )
    a = _claim("a", prop_a)  # the prop_b-holder is absent from the corpus
    assert derived_rebut_edges([a]) == ()


def test_claim_without_conclusion_is_excluded():
    prop_b = Proposition(direction=Direction.NEGATIVE, estimand="e", descriptor="d-neg")
    prop_a = Proposition(
        direction=Direction.POSITIVE, estimand="e", descriptor="d-pos",
        neighborhood=(NeighborEdge(kind=NeighborEdgeKind.INCOMPATIBLE_WITH,
                                   target=prop_b.content_hash),),
    )
    a = _claim("a", prop_a)
    b = _claim("b", prop_b)
    none_claim = Claim(
        id="c", title="c", pattern=PatternRef(id="p", version="v1"),
        leaves=(_leaf(),), status=Status.LICENSED, conclusion=None,
    )
    # none_claim contributes nothing; still exactly the 2 mutual a<->b edges
    assert len(derived_rebut_edges([a, b, none_claim])) == 2


def _sat(mid, verdict):
    return Satisfaction(
        verdict=verdict,
        materialization=MaterializationContext(id=mid, api_version="0.9", data_version="db@x"),
    )


def test_refuted_and_undetermined_become_undermine_edges():
    sats = [
        _sat("m1", SatisfactionVerdict.REFUTED),
        _sat("m2", SatisfactionVerdict.UNDETERMINED),
        _sat("m3", SatisfactionVerdict.SATISFIED),
    ]
    edges = undermine_edges_from_failed_satisfactions("claimX", sats)
    assert len(edges) == 2
    assert all(e.kind == DefeatEdgeKind.UNDERMINE and e.target == "claimX" for e in edges)
    assert {e.source for e in edges} == {"refutation:m1", "refutation:m2"}


def test_all_satisfied_yields_no_edges():
    sats = [_sat("m1", SatisfactionVerdict.SATISFIED)]
    assert undermine_edges_from_failed_satisfactions("claimX", sats) == ()


def test_public_api_exports():
    import polymer_grammar as pg

    for name in [
        "DefeatEdge", "DefeatEdgeKind", "ATTACK_KINDS", "effective_defeats", "grounded_extension",
        "derived_rebut_edges", "undermine_edges_from_failed_satisfactions",
        "BlameAssignment", "BlameSet", "BlameVerdict", "aggregate_blame", "duhem_status",
    ]:
        assert hasattr(pg, name), f"{name} not exported from polymer_grammar"


def test_defeat_edge_provisional_defaults_false():
    assert DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT).provisional is False


def test_provisional_edge_inert_without_licensed_source():
    e = DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True)
    strength = {"d": None, "b": None}
    assert effective_defeats((e,), strength) == frozenset()                          # default empty
    assert effective_defeats((e,), strength, licensed_ids=frozenset()) == frozenset()


def test_provisional_edge_effective_when_source_licensed():
    e = DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True)
    strength = {"d": None, "b": None}
    assert effective_defeats((e,), strength, licensed_ids=frozenset({"d"})) == frozenset({("d", "b")})


def test_nonprovisional_edge_still_effective_from_conjectured_source():
    # LOAD-BEARING: a NORMAL edge from a strengthless source is STILL effective (#1 frontier semantics)
    e = DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT)  # provisional=False
    strength = {"d": None, "b": None}
    assert effective_defeats((e,), strength) == frozenset({("d", "b")})


def test_grounded_extension_honors_provisional_activation():
    e_ba = DefeatEdge(source="b", target="a", kind=DefeatEdgeKind.REBUT)
    e_db = DefeatEdge(source="d", target="b", kind=DefeatEdgeKind.REBUT, provisional=True)
    strength = {"a": None, "b": None, "d": None}
    ids = ["a", "b", "d"]
    g0 = grounded_extension(ids, (e_ba, e_db), strength)                       # d not licensed -> inert
    assert "a" not in g0 and "b" in g0 and "d" in g0
    g1 = grounded_extension(ids, (e_ba, e_db), strength, licensed_ids=frozenset({"d"}))
    assert "a" in g1 and "b" not in g1 and "d" in g1                           # d licensed -> d defeats b -> a reinstated
