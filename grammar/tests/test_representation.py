import pytest
from pydantic import ValidationError

from polymer_grammar import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    PatternRef,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
)
from polymer_grammar.representation import (
    META_TIER_ALLOWED_CLOSURES,
    META_TIER_REQUIRED_ROUTE,
    ConstraintTarget,
    OntologyTermTarget,
    PatternTarget,
    RepresentationRevision,
    RevisionOperation,
    meets_meta_tier_bar,
)

_PR = PatternRef(id="adjusted_effect", version="v1")
_PR2 = PatternRef(id="simple_correlation", version="v1")


def _rev(operation, target, rationale="because", proposed_definition=None):
    return RepresentationRevision(
        operation=operation, target=target, rationale=rationale,
        proposed_definition=proposed_definition,
    )


def test_add_pattern_builds():
    r = _rev(RevisionOperation.ADD, PatternTarget(patterns=(_PR,)))
    assert r.operation == RevisionOperation.ADD
    assert r.target.kind == "pattern"


def test_add_ontology_term_builds():
    r = _rev(RevisionOperation.ADD, OntologyTermTarget(term_id="HP:0001250"))
    assert r.target.kind == "ontology_term"


def test_deprecate_pattern_and_ontology_term_build():
    assert _rev(RevisionOperation.DEPRECATE, PatternTarget(patterns=(_PR,)))
    assert _rev(RevisionOperation.DEPRECATE, OntologyTermTarget(term_id="GO:0008150"))


def test_merge_requires_two_patterns():
    assert _rev(RevisionOperation.MERGE, PatternTarget(patterns=(_PR, _PR2)))
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.MERGE, PatternTarget(patterns=(_PR,)))  # only 1
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.MERGE, OntologyTermTarget(term_id="x"))  # not a pattern


def test_relax_requires_constraint_target():
    assert _rev(RevisionOperation.RELAX, ConstraintTarget(name="at_least_one_exclusion"))
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.RELAX, PatternTarget(patterns=(_PR,)))


def test_add_deprecate_reject_constraint_and_wrong_pattern_count():
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.ADD, ConstraintTarget(name="c"))
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.DEPRECATE, PatternTarget(patterns=(_PR, _PR2)))  # !=1


def test_rationale_required_nonempty():
    with pytest.raises(ValidationError):
        _rev(RevisionOperation.ADD, OntologyTermTarget(term_id="x"), rationale="")


def test_empty_term_id_and_constraint_name_rejected():
    with pytest.raises(ValidationError):
        OntologyTermTarget(term_id="")
    with pytest.raises(ValidationError):
        ConstraintTarget(name="")


def test_target_dispatches_by_kind_from_dict():
    r = RepresentationRevision.model_validate(
        {"operation": "add", "target": {"kind": "ontology_term", "term_id": "HP:1"},
         "rationale": "x"}
    )
    assert isinstance(r.target, OntologyTermTarget)


def test_revision_is_hashable():
    r = _rev(RevisionOperation.ADD, OntologyTermTarget(term_id="x"))
    assert len({r, r}) == 1  # usable in a set -> content-addressable


def _lic(route, closure, n_mats, rivals=()):
    mats = [MaterializationContext(id=f"M{i}", api_version="v1", data_version="d1")
            for i in range(n_mats)]
    sats = tuple(Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=m) for m in mats)
    return Licensing(route=route, rival_set_closure=closure, rivals_considered=rivals, satisfactions=sats)


def test_meets_meta_tier_bar_true_cases():
    assert meets_meta_tier_bar(_lic(LicenseRoute.REPLICATION, RivalSetClosure.ENUMERATED, 2, ("r1",)))
    assert meets_meta_tier_bar(_lic(LicenseRoute.REPLICATION, RivalSetClosure.ONTOLOGY_BOUNDED, 2))


def test_meets_meta_tier_bar_false_cases():
    # severe test (single materialization) -> below the bar
    assert not meets_meta_tier_bar(_lic(LicenseRoute.SEVERE_TEST, RivalSetClosure.ENUMERATED, 1, ("r1",)))
    # replication but an OPEN rival closure -> below the bar
    assert not meets_meta_tier_bar(_lic(LicenseRoute.REPLICATION, RivalSetClosure.OPEN_ACKNOWLEDGED, 2))


def test_mdl_gate_route_meets_meta_tier_bar():
    # an MDL_GATE-routed licensing clears the meta-tier bar (the compression evidence stands in
    # for human replication); it does NOT need a REPLICATION route or a closed rival set.
    lic = _lic(LicenseRoute.MDL_GATE, RivalSetClosure.OPEN_ACKNOWLEDGED, 1)
    assert meets_meta_tier_bar(lic) is True


def test_existing_qualitative_route_still_passes_alongside_mdl_gate():
    assert meets_meta_tier_bar(_lic(LicenseRoute.REPLICATION, RivalSetClosure.ENUMERATED, 2, ("r1",)))


def test_severe_test_open_still_fails_with_mdl_gate_added():
    assert not meets_meta_tier_bar(
        _lic(LicenseRoute.SEVERE_TEST, RivalSetClosure.OPEN_ACKNOWLEDGED, 1)
    )


def test_meta_tier_constants():
    assert META_TIER_REQUIRED_ROUTE == LicenseRoute.REPLICATION
    assert RivalSetClosure.ENUMERATED in META_TIER_ALLOWED_CLOSURES
    assert RivalSetClosure.ONTOLOGY_BOUNDED in META_TIER_ALLOWED_CLOSURES
    assert RivalSetClosure.OPEN_ACKNOWLEDGED not in META_TIER_ALLOWED_CLOSURES


def test_representation_symbols_exported_from_package():
    import polymer_grammar as pg

    for name in (
        "RevisionOperation", "PatternTarget", "OntologyTermTarget", "ConstraintTarget",
        "RevisionTarget", "RepresentationRevision", "is_representation_revision",
        "meets_meta_tier_bar", "META_TIER_REQUIRED_ROUTE", "META_TIER_ALLOWED_CLOSURES",
    ):
        assert hasattr(pg, name), f"missing export: {name}"
