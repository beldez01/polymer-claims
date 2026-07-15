"""F3 reference-table materializer — reported reference values become two-stratum CONJECTURED claims."""
from __future__ import annotations

import pytest
from polymer_grammar.leaf import MeasurementBasis
from polymer_grammar.provenance import GenerationMode
from polymer_grammar.status import Status

from polymer_claims.reference_materializer import (
    ch7_biophysical_prior_claims,
    materialize_reference_table,
    reference_quantity_claim,
)


def test_reference_claim_is_two_stratum_conjectured_literature():
    c = reference_quantity_claim(
        claim_id="ref-x", title="a reported value", value=3.0, unit="nm",
        measurement_basis=MeasurementBasis.FUNDAMENTAL,
        source_ref="Doe 2020", source_title="A paper")
    # Two-stratum: a reported value is CONJECTURED (never self-licenses) + LITERATURE_EXTRACTED.
    assert c.status is Status.CONJECTURED
    assert c.provenance.generated_by is GenerationMode.LITERATURE_EXTRACTED
    assert c.provenance.method == "Doe 2020"
    assert c.leaves[0].value == 3.0 and c.leaves[0].unit == "nm"


def test_materialize_table_prefixes_ids_and_maps_rows():
    rows = [
        dict(key="a", title="A", value=1.0, formula="x/y", source_ref="R", source_title="T"),
        dict(key="b", title="B", value=2.0, low=1.0, high=3.0, formula="p/q", source_ref="R", source_title="T"),
    ]
    claims = materialize_reference_table(rows, id_prefix="tbl")
    assert [c.id for c in claims] == ["tbl-a", "tbl-b"]
    assert claims[1].leaves[0].low == 1.0 and claims[1].leaves[0].high == 3.0
    assert all(c.status is Status.CONJECTURED for c in claims)


def test_missing_required_field_raises_not_fabricates():
    # A row missing `value` must fail loudly, never invent one.
    with pytest.raises(TypeError):
        materialize_reference_table([dict(key="a", title="A", source_ref="R", source_title="T")],
                                    id_prefix="tbl")


def test_ch7_biophysical_priors_materialize_from_the_plan():
    claims = ch7_biophysical_prior_claims()
    by_id = {c.id: c for c in claims}
    assert "ch7-bret-r0" in by_id and "ch7-sensor-dynamic-range" in by_id
    r0 = by_id["ch7-bret-r0"]
    assert r0.leaves[0].low == 4.0 and r0.leaves[0].high == 5.0 and r0.leaves[0].unit == "nm"
    assert all(c.status is Status.CONJECTURED for c in claims)          # two-stratum
    assert all(c.provenance.generated_by is GenerationMode.LITERATURE_EXTRACTED for c in claims)
