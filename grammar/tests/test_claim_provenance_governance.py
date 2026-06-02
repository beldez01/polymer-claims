from polymer_grammar.claim import Claim
from polymer_grammar.governance import AccessScope, Governance, HazardClass
from polymer_grammar.leaf import MeasurementBasis, QuantityLeaf
from polymer_grammar.pattern import PatternRef
from polymer_grammar.provenance import GenerationMode, Provenance
from polymer_grammar.status import Status


def _leaf():
    return QuantityLeaf(value=1.0, measurement_basis=MeasurementBasis.DERIVED, formula="f")


def _claim(**kw):
    base = dict(id="c", title="c", pattern=PatternRef(id="p", version="v1"),
                leaves=(_leaf(),), status=Status.LICENSED)
    base.update(kw)
    return Claim(**base)


def test_claim_carries_provenance_and_governance():
    prov = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="a1", search_cardinality=12)
    gov = Governance(hazard_class=HazardClass.DUAL_USE, access_scope=AccessScope.CONTROLLED)
    c = _claim(provenance=prov, governance=gov)
    assert c.provenance.search_cardinality == 12
    assert c.governance.hazard_class == HazardClass.DUAL_USE


def test_provenance_and_governance_optional_backcompat():
    c = _claim()
    assert c.provenance is None
    assert c.governance is None
