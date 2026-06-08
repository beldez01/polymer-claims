"""Tests for the per-claim display-card helper (`claim_detail` / `derive_rejection_reason`)."""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    GenerationMode,
    PatternRef,
    Provenance,
    Status,
    StrengthVector,
)

from polymer_claims.claim_detail import claim_detail, derive_rejection_reason
from tests.conftest import make_claim, make_plan

_PATTERN_ID = "adjusted_effect"


def test_licensed_satisfied_const_claim():
    claim = make_claim(
        "lic", status=Status.LICENSED, plan=make_plan(0.01, 0.05, Comparator.LT)
    )
    d = claim_detail(claim)
    assert d["id"] == "lic"
    assert d["title"] == "claim lic"
    assert d["status"] == "licensed"
    assert d["pattern_id"] == _PATTERN_ID
    assert d["subject_term"] == "term-lic"
    assert d["plan"] == {"impl": "builtin::const", "value": 0.01}
    assert d["criterion"] == {
        "comparator": "lt",
        "threshold": 0.05,
        "tolerance": None,
    }
    assert d["criterion_satisfied"] is True
    assert d["rejection_reason"] is None


def test_rejected_failing_const_claim():
    claim = make_claim(
        "rej", status=Status.REJECTED, plan=make_plan(0.08, 0.05, Comparator.LT)
    )
    d = claim_detail(claim)
    assert d["status"] == "rejected"
    assert d["criterion_satisfied"] is False
    assert (
        d["rejection_reason"]
        == "criterion not met — const(0.08) lt 0.05 is FALSE"
    )
    assert derive_rejection_reason(claim) == d["rejection_reason"]


def test_rejected_passing_const_claim():
    claim = make_claim(
        "rejp", status=Status.REJECTED, plan=make_plan(0.01, 0.05, Comparator.LT)
    )
    d = claim_detail(claim)
    assert d["criterion_satisfied"] is True
    assert (
        d["rejection_reason"]
        == "criterion met but rejected — likely defeated by a rival, a duplicate, "
        "or the selective-significance bar"
    )


def test_no_plan_rejected_and_not_rejected():
    rejected = make_claim("np_rej", status=Status.REJECTED, plan=None)
    d = claim_detail(rejected)
    assert d["plan"] is None
    assert d["criterion"] is None
    assert d["criterion_satisfied"] is None
    assert (
        d["rejection_reason"]
        == "rejected — no const criterion to evaluate (likely defeated or significance bar)"
    )

    conj = make_claim("np_conj", status=Status.CONJECTURED, plan=None)
    dc = claim_detail(conj)
    assert dc["plan"] is None
    assert dc["criterion"] is None
    assert dc["criterion_satisfied"] is None
    assert dc["rejection_reason"] is None


def test_subject_term_from_categorical_leaf():
    claim = Claim(
        id="cat",
        title="cat claim",
        pattern=PatternRef(id=_PATTERN_ID, version="v1"),
        leaves=(CategoricalLeaf(ontology_term="HP:0001234"),),
        status=Status.CONJECTURED,
    )
    assert claim_detail(claim)["subject_term"] == "HP:0001234"


def test_strength_passthrough_and_none():
    sv = StrengthVector(
        magnitude=0.1,
        certainty=0.2,
        evidence_against_null=0.3,
        severity=0.4,
        world_contact=0.5,
        explanatory_virtue=0.6,
    )
    claim = Claim(
        id="s",
        title="s",
        pattern=PatternRef(id=_PATTERN_ID, version="v1"),
        leaves=(CategoricalLeaf(ontology_term="t"),),
        status=Status.CONJECTURED,
        strength=sv,
    )
    assert claim_detail(claim)["strength"] == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

    none_claim = make_claim("snone", status=Status.CONJECTURED, plan=None)
    assert claim_detail(none_claim)["strength"] is None


def test_provenance_passthrough_and_none():
    prov = Provenance(
        generated_by=GenerationMode.AGENT_GENERATED,
        agent_id="agent-7",
        method="template",
        search_cardinality=1,
    )
    claim = Claim(
        id="p",
        title="p",
        pattern=PatternRef(id=_PATTERN_ID, version="v1"),
        leaves=(CategoricalLeaf(ontology_term="t"),),
        status=Status.CONJECTURED,
        provenance=prov,
    )
    assert claim_detail(claim)["provenance"] == {
        "generated_by": "agent_generated",
        "agent_id": "agent-7",
        "method": "template",
    }

    none_claim = make_claim("pnone", status=Status.CONJECTURED, plan=None)
    assert claim_detail(none_claim)["provenance"] is None


def test_rationale_surfaced_top_level_and_none():
    prov = Provenance(
        generated_by=GenerationMode.AGENT_GENERATED,
        agent_id="agent-7",
        search_cardinality=1,
        rationale="mediation weakens at dose",
    )
    claim = Claim(
        id="r",
        title="r",
        pattern=PatternRef(id=_PATTERN_ID, version="v1"),
        leaves=(CategoricalLeaf(ontology_term="t"),),
        status=Status.CONJECTURED,
        provenance=prov,
    )
    assert claim_detail(claim)["rationale"] == "mediation weakens at dose"

    none_claim = make_claim("rnone", status=Status.CONJECTURED, plan=None)
    assert claim_detail(none_claim)["rationale"] is None
