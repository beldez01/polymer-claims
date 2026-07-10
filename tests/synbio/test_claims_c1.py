"""Task 2 — C1: single Watson-Crick mismatch discrimination energy (a FUNDAMENTAL quantity)."""
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.provenance import GenerationMode
from polymer_grammar.status import Status

from polymer_claims.synbio.claims import mismatch_energy_claim


def test_c1_is_fundamental_energy_and_conjectured():
    claim = mismatch_energy_claim()
    leaf = claim.leaves[0]
    assert isinstance(leaf, QuantityLeaf)
    assert leaf.measurement_basis is MeasurementBasis.FUNDAMENTAL
    assert leaf.unit == "kcal/mol"
    assert leaf.value == 2.0
    assert leaf.uncertainty == 1.0
    # A reported fact is CONJECTURED — never licensed without recompute (spec §3).
    assert claim.status is Status.CONJECTURED
    # Reported stratum uses LITERATURE_EXTRACTED, not AGENT_GENERATED.
    assert claim.provenance is not None
    assert claim.provenance.generated_by is GenerationMode.LITERATURE_EXTRACTED
    assert claim.provenance.search_cardinality == 1
