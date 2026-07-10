"""Task 3 — C2: ADAR RNA-sensor dynamic range (a DERIVED quantity) + the context gap."""
import pytest

from polymer_grammar.leaf import MeasurementBasis
from polymer_grammar.provenance import GenerationMode

from polymer_claims.synbio.claims import adar_dynamic_range_claim


def test_c2_derived_requires_formula_and_no_unit():
    claim = adar_dynamic_range_claim()
    leaf = claim.leaves[0]
    assert leaf.measurement_basis is MeasurementBasis.DERIVED
    # The validator forbids a unit on DERIVED and requires a formula.
    assert leaf.unit is None
    assert leaf.formula
    assert leaf.value == 277.0
    assert claim.provenance.generated_by is GenerationMode.LITERATURE_EXTRACTED


@pytest.mark.xfail(
    reason="grammar gap (general-class): QuantityLeaf has no field for the context a derived "
    "statistic holds in (ADAR 277-fold is cell-line-specific); see "
    "docs/superpowers/notes/2026-07-10-synbio-grammar-gaps.md",
    strict=True,
)
def test_c2_context_conditioning_gap():
    # WANT: QuantityLeaf to carry the measurement context (e.g. cell line / assay condition).
    # SCHEMA tripwire — flips the day QuantityLeaf GAINS a `context` field, forcing a
    # deliberate review of the resolution (spec §5 / GAP-2). A value-based check would miss
    # it: the resolution field is optional and defaults to None, so populating it is a
    # separate step from growing the schema.
    leaf = adar_dynamic_range_claim().leaves[0]
    assert "context" in type(leaf).model_fields
