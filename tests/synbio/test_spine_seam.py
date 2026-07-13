from polymer_claims.synbio.spine import expression_floor_claim, two_leg_floor_agreement
from polymer_grammar.leaf import QuantityLeaf
from polymer_grammar.status import Status

def test_expression_floor_claim_shape_conjectured_with_context():
    c = expression_floor_claim("RUNX1T1", tissue="AML", floor_tpm=13.0)
    leaf = c.leaves[0]
    assert isinstance(leaf, QuantityLeaf)
    assert leaf.context is not None and leaf.context.tissue == "AML"
    assert leaf.context.assay == "RNA-seq TPM"
    assert c.status is Status.CONJECTURED       # scaffold only — no license this session

def test_two_leg_agreement_requires_both():
    assert two_leg_floor_agreement(20.0, 18.0, floor=13.0) is True
    assert two_leg_floor_agreement(20.0, 5.0, floor=13.0) is False   # leg B disagrees
    assert two_leg_floor_agreement(2.0, 3.0, floor=13.0) is False    # both below
