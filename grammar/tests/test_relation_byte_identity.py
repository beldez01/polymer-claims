"""Byte-identity guard for relation-free claims (cross-arm-relations Task 4).

Tasks 1-3 added `ClaimSetSubject` (a new Subject union member), `RelationLeaf` (a new
Leaf union member), and a relation module. Both additions are purely additive to
existing discriminated unions. This test pins the invariant that an ordinary,
relation-free `Claim` — one built from pre-existing leaf/subject variants — still
serializes byte-identically after those additions: no new key leaks onto claims that
never touch a relation, and no existing field's encoding shifted.

If this test fails, a prior task added a non-defaulted field to an existing model
(Claim, QuantityLeaf, GeneOrProtein, ...) — that is a regression to fix in the
offending task, not something this test should paper over.
"""
import json

from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import Status
from polymer_grammar.subject import GeneOrProtein, GeneOrProteinIdentifiers
from polymer_grammar.strength import StrengthVector


def _representative_claim() -> Claim:
    """An ordinary claim: QuantityLeaf + a real (non-relation) Subject variant."""
    leaf = QuantityLeaf(
        value=-0.238,
        measurement_basis=MeasurementBasis.DERIVED,
        formula="ppcor::pcor.test(curvature, co_rate | gc)",
    )
    subject = GeneOrProtein(
        id="HGNC:11998",
        display="TP53",
        identifiers=GeneOrProteinIdentifiers(hgnc="HGNC:11998"),
        entity_type="gene",
    )
    strength = StrengthVector(
        magnitude=0.7, certainty=0.3, evidence_against_null=0.7,
        severity=0.7, world_contact=0.7, explanatory_virtue=0.7,
    )
    return Claim(
        id="recomb_curvature_co",
        title="Curvature disfavors crossover after GC control",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=[leaf],
        subject=subject,
        status=Status.LICENSED,
        strength=strength,
    )


def test_relation_free_claim_serialization_byte_identical_round_trip():
    """Adding RelationLeaf/ClaimSetSubject union members must not perturb an
    ordinary claim's serialization: dump -> parse -> dump is byte-identical."""
    claim = _representative_claim()
    s = claim.model_dump_json()
    assert Claim.model_validate(json.loads(s)).model_dump_json() == s


def test_relation_free_claim_has_no_relation_keys():
    """A claim that never touches a relation carries no relation/claim_set vocabulary."""
    s = _representative_claim().model_dump_json()
    payload = json.loads(s)
    assert payload["subject"]["kind"] == "gene_or_protein"
    assert payload["leaves"][0]["kind"] == "quantity"
    assert "relation_kind" not in s
    assert "claim_set" not in s
