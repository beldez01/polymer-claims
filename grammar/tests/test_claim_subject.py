from polymer_grammar.claim import Claim
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.status import Status
from polymer_grammar.subject import GeneOrProtein, GeneOrProteinIdentifiers


def _leaf():
    return QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f")


def _claim(**kw):
    base = dict(id="c", title="c", pattern=PatternRef(id="p", version="v1"),
                leaves=(_leaf(),), status=Status.LICENSED)
    base.update(kw)
    return Claim(**base)


def test_claim_carries_a_subject():
    g = GeneOrProtein(id="HGNC:11998", display="TP53",
                      identifiers=GeneOrProteinIdentifiers(hgnc="HGNC:11998"), entity_type="gene")
    c = _claim(subject=g)
    assert c.subject is g
    assert c.subject.kind == "gene_or_protein"


def test_claim_subject_is_optional_backcompat():
    c = _claim()
    assert c.subject is None
