from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
import pytest

from polymer_grammar.representation import (
    ConstraintTarget,
    OntologyTermTarget,
    PatternTarget,
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


@pytest.mark.parametrize(
    "revision",
    [
        RepresentationRevision(operation=RevisionOperation.ADD,
                               target=OntologyTermTarget(term_id="HP:1"), rationale="r"),
        RepresentationRevision(operation=RevisionOperation.DEPRECATE,
                               target=PatternTarget(patterns=(PatternRef(id="a", version="v1"),)),
                               rationale="r"),
        RepresentationRevision(operation=RevisionOperation.MERGE,
                               target=PatternTarget(patterns=(PatternRef(id="a", version="v1"),
                                                              PatternRef(id="b", version="v1"))),
                               rationale="r"),
        RepresentationRevision(operation=RevisionOperation.RELAX,
                               target=ConstraintTarget(name="at_least_one_exclusion"), rationale="r"),
    ],
)
def test_claim_nested_discriminated_target_round_trips(revision):
    # pins that EACH target subtype survives a Claim-level model_dump/model_validate round-trip
    # (the nested discriminated union is exactly the wiring that can silently regress).
    c = _claim(representation_revision=revision)
    c2 = Claim.model_validate(c.model_dump())
    assert c2 == c
    assert type(c2.representation_revision.target) is type(revision.target)


def test_representation_revision_orthogonal_to_status():
    conj = _claim(status=Status.CONJECTURED, representation_revision=_rev())
    lic = _claim(status=Status.LICENSED, representation_revision=_rev())
    assert is_representation_revision(conj) and is_representation_revision(lic)
