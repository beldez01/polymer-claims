from polymer_grammar import Status

from polymer_claims.pharmaco_adapters import marker_drug_claim, pharmaco_oracle_registry
from polymer_claims.capabilities import CAPABILITY_CELLS, bind


def test_cell_registered_and_binding_resolves():
    assert CAPABILITY_CELLS.resolve("pharmaco::assoc", "v1") is not None
    b = bind("pharmaco::assoc", "v1")  # must not raise
    assert b.trust_profile


def test_marker_drug_claim_shape():
    c = marker_drug_claim(
        "pgx-CDKN2A-Palbociclib", ref="se:gdsc_pharmaco@1", marker="CDKN2A",
        drug="Palbociclib", drug_chebi_uri="http://purl.obolibrary.org/obo/CHEBI_85993",
        search_cardinality=8)
    assert c.status == Status.PENDING
    assert c.pattern.id == "adjusted_effect"
    assert c.subject.kind == "composite" and len(c.subject.parts) == 2
    assert c.leaves[0].kind == "categorical"  # Polymer-native; no engine r_adj in the claim
    assert c.provenance.generated_by.value == "agent_generated"
    assert c.provenance.agent_id == "pharmaco-mechanism-v1"
    # composite subject is admitted by the apparatus domain
    dom = pharmaco_oracle_registry().dossiers[0].applicability_domain
    assert "composite" in dom.subject_kinds
