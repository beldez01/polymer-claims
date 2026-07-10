"""Task 3 — C2: ADAR RNA-sensor dynamic range (a DERIVED quantity); GAP-2 context resolved."""
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


def test_c2_context_conditioning_resolved():
    # GAP-2 RESOLVED (Phase 2a): QuantityLeaf now carries MeasurementContext, and C2 populates
    # it with the assay the 277-fold was measured in. (Was a strict-xfail schema tripwire.)
    leaf = adar_dynamic_range_claim().leaves[0]
    assert "context" in type(leaf).model_fields  # the schema grew
    assert leaf.context is not None               # and C2 populates it
    assert leaf.context.assay                      # with the known assay context
