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
    # WANT: a field carrying the measurement context (e.g. the cell line / assay condition).
    # This xfail is a tripwire — it flips to a failure the day a context field is added,
    # forcing a deliberate review of the resolution.
    claim = adar_dynamic_range_claim()
    leaf = claim.leaves[0]
    assert getattr(leaf, "context", None) is not None
