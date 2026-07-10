"""Task 5 — C5: the affinity–discrimination law (a warranted proposition, and a defeater)."""
from polymer_grammar.leaf import PropositionLeaf
from polymer_grammar.provenance import GenerationMode
from polymer_grammar.status import Status

from polymer_claims.synbio.claims import affinity_discrimination_law_claim


def test_c5_is_a_warranted_proposition():
    claim = affinity_discrimination_law_claim()
    leaf = claim.leaves[0]
    assert isinstance(leaf, PropositionLeaf)
    assert leaf.data
    assert leaf.warrant
    assert leaf.rebuttal  # a law worth its salt names where it fails
    assert leaf.warrant_type == "mechanistic_analogy"
    # Reported stratum → CONJECTURED. As a defeater it may only author provisional edges (GAP-4).
    assert claim.status is Status.CONJECTURED
    assert claim.provenance.generated_by is GenerationMode.LITERATURE_EXTRACTED
