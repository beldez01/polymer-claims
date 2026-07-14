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


def test_measurement_context_one_field_ok():
    c = MeasurementContext(tissue="AML")
    assert c.tissue == "AML" and c.assay is None


def test_measurement_context_rejects_all_none():
    # An all-None context is meaningless — use context=None instead (single representation).
    with pytest.raises(ValueError):
        MeasurementContext()


def test_fundamental_discipline_unchanged():
    # Regression: unit is still forbidden on a DERIVED quantity.
    with pytest.raises(ValueError):
        QuantityLeaf(value=1.0, unit="x", measurement_basis=MeasurementBasis.DERIVED, formula="f")


# --- GAP-8: optional gene/locus sub-key (additive, byte-identical when unset) -----------------

# Captured from the pre-field grammar: a context without target_locus keeps its exact shape (the
# other fields' null-emission is pre-existing and must be preserved).
_CTX_NO_LOCUS_BASELINE = '{"tissue":"AML","cell_line":null,"assay":null,"condition":null}'


def test_context_without_locus_is_byte_identical():
    c = MeasurementContext(tissue="AML")
    assert c.model_dump_json() == _CTX_NO_LOCUS_BASELINE
    assert "target_locus" not in c.model_dump()


def test_target_locus_carried_and_round_trips():
    c = MeasurementContext(target_locus="TET2")  # a property of the locus, not tissue/assay/condition
    assert c.target_locus == "TET2"
    dumped = c.model_dump_json()
    assert '"target_locus":"TET2"' in dumped
    assert MeasurementContext.model_validate_json(dumped).target_locus == "TET2"


def test_locus_only_context_is_valid():
    # A gene/locus identity alone is real context — it satisfies the at-least-one-field rule.
    c = MeasurementContext(target_locus="TET2")
    assert c.tissue is None and c.target_locus == "TET2"
