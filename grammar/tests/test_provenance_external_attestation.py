from polymer_grammar.provenance import GenerationMode, Provenance


def test_external_attestation_member_exists():
    assert GenerationMode.EXTERNAL_ATTESTATION.value == "external_attestation"


def test_provenance_accepts_external_attestation():
    p = Provenance(generated_by=GenerationMode.EXTERNAL_ATTESTATION,
                   search_cardinality=1, method="doi:10.1056/x")
    assert p.generated_by is GenerationMode.EXTERNAL_ATTESTATION
    assert p.method == "doi:10.1056/x"
