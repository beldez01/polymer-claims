from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.representation import (
    OntologyTermTarget,
    RepresentationRevision,
    RevisionOperation,
    is_representation_revision,
)
from polymer_grammar.status import Status


def _leaf():
    return QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f")


def _claim(**kw):
    base = dict(id="c", title="c", pattern=PatternRef(id="p", version="v1"),
                leaves=(_leaf(),), status=Status.CONJECTURED)
    base.update(kw)
    return Claim(**base)


def _rev():
    return RepresentationRevision(
        operation=RevisionOperation.ADD,
        target=OntologyTermTarget(term_id="HP:0001250"),
        rationale="needed to express the seizure phenotype",
    )


def test_representation_revision_is_optional_backcompat():
    c = _claim()
    assert c.representation_revision is None
    assert is_representation_revision(c) is False


def test_claim_carries_a_representation_revision():
    c = _claim(representation_revision=_rev())
    assert c.representation_revision is not None
    assert is_representation_revision(c) is True
    assert c.representation_revision.operation == RevisionOperation.ADD


def test_meta_claim_is_hashable_and_round_trips():
    c = _claim(representation_revision=_rev())
    hash(c)  # frozen + hashable must hold with the new field
    Claim.model_validate(c.model_dump())  # valid round-trip


def test_representation_revision_orthogonal_to_status():
    conj = _claim(status=Status.CONJECTURED, representation_revision=_rev())
    lic = _claim(status=Status.LICENSED, representation_revision=_rev())
    assert is_representation_revision(conj) and is_representation_revision(lic)
