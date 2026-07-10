"""GAP-2 resolution — optional MeasurementContext on QuantityLeaf (Wayland Phase 2a).

The load-bearing property is BYTE-IDENTITY: a context-less QuantityLeaf must serialize exactly
as it did before the field existed (no new key), so every existing corpus is unaffected.
"""
import pytest

from polymer_grammar.leaf import MeasurementBasis, MeasurementContext, QuantityLeaf

# Captured from the pre-change grammar (the byte-identity baseline).
_FUND_BASELINE = (
    '{"kind":"quantity","value":2.0,"unit":"kcal/mol","uncertainty":1.0,'
    '"measurement_basis":"fundamental","formula":null,"dimension":null}'
)
_DERV_BASELINE = (
    '{"kind":"quantity","value":277.0,"unit":null,"uncertainty":null,'
    '"measurement_basis":"derived","formula":"edited/unedited","dimension":null}'
)


def test_context_less_leaf_is_byte_identical():
    f = QuantityLeaf(
        value=2.0, unit="kcal/mol", uncertainty=1.0,
        measurement_basis=MeasurementBasis.FUNDAMENTAL,
    )
    d = QuantityLeaf(
        value=277.0, measurement_basis=MeasurementBasis.DERIVED, formula="edited/unedited",
    )
    # No "context":null leaks into the output; bytes match the pre-field baseline exactly.
    assert f.model_dump_json() == _FUND_BASELINE
    assert d.model_dump_json() == _DERV_BASELINE
    assert "context" not in f.model_dump()


def test_context_bearing_leaf_round_trips():
    ctx = MeasurementContext(tissue="AML", assay="RNA-seq TPM")
    leaf = QuantityLeaf(
        value=20.0, measurement_basis=MeasurementBasis.DERIVED, formula="tpm", context=ctx,
    )
    dumped = leaf.model_dump_json()
    assert '"context"' in dumped
    back = QuantityLeaf.model_validate_json(dumped)
    assert back.context.tissue == "AML"
    assert back.context.assay == "RNA-seq TPM"


def test_measurement_context_all_optional():
    c = MeasurementContext()
    assert c.tissue is None and c.cell_line is None and c.assay is None and c.condition is None


def test_fundamental_discipline_unchanged():
    # Regression: unit is still forbidden on a DERIVED quantity.
    with pytest.raises(ValueError):
        QuantityLeaf(value=1.0, unit="x", measurement_basis=MeasurementBasis.DERIVED, formula="f")
