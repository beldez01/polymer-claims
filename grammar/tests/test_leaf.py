import pytest
from pydantic import TypeAdapter, ValidationError

from polymer_grammar.leaf import (
    CategoricalLeaf,
    ExistenceLeaf,
    Leaf,
    MeasurementBasis,
    PropositionLeaf,
    QuantityLeaf,
)

ADAPTER = TypeAdapter(Leaf)


def test_quantity_fundamental_may_carry_unit():
    leaf = QuantityLeaf(
        value=37.0, unit="Cel", uncertainty=0.5,
        measurement_basis=MeasurementBasis.FUNDAMENTAL,
    )
    assert leaf.kind == "quantity"
    assert leaf.unit == "Cel"


def test_quantity_derived_requires_formula_and_forbids_unit():
    leaf = QuantityLeaf(
        value=-0.238, measurement_basis=MeasurementBasis.DERIVED,
        formula="ppcor::pcor.test(curvature, co_rate | gc)",
    )
    assert leaf.formula is not None
    with pytest.raises(ValidationError):
        QuantityLeaf(value=-0.238, unit="ratio", measurement_basis=MeasurementBasis.DERIVED,
                     formula="x")  # unit forbidden on derived


def test_quantity_derived_without_formula_rejected():
    with pytest.raises(ValidationError):
        QuantityLeaf(value=-0.18, measurement_basis=MeasurementBasis.DERIVED)


def test_categorical_carries_ontology_term_not_unit():
    leaf = CategoricalLeaf(ontology_term="SO:0000657", assay="ChromHMM")
    assert leaf.kind == "categorical"


def test_existence_distinguishes_absence_from_untested():
    leaf = ExistenceLeaf(state="not_detected", detection_limit=0.01)
    assert leaf.kind == "existence"


def test_proposition_leaf_is_a_toulmin_warrant():
    leaf = PropositionLeaf(
        data="cross-cell-type methylation variance is class-specific",
        warrant="KZFP/TRIM28 silencing targets young LTRs",
        warrant_type="mechanistic_analogy",
    )
    assert leaf.kind == "proposition"


def test_discriminated_union_dispatches_on_kind():
    leaf = ADAPTER.validate_python({"kind": "existence", "state": "observed"})
    assert isinstance(leaf, ExistenceLeaf)
