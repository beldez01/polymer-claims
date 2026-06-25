from polymer_claims.real_kernel_proof import load_pins

def test_pins_load_and_have_schema():
    pins = load_pins()
    assert pins["contract_uid"] == "tcga_laml_idh@2"
    inp = pins["inputs"]
    assert set(inp_key for inp_key in inp) == {"xena", "cbio_mutations", "cbio_sequenced"}
    assert inp["xena"]["filename"] == "TCGA-LAML.methylation450.tsv.gz"
    assert "sha256" in inp["xena"] and "url" in inp["xena"]
    assert inp["cbio_mutations"]["commit"]                       # datahub commit pinned
    assert inp["cbio_sequenced"]["api_endpoint"].startswith("https://")
    exp = pins["expected"]
    for key in ("contract_uid", "contract_checksum", "canonical_checksum", "dimnames_hash",
                "group_digest", "idh_mut_n", "wt_n", "n_probes", "n_dmps", "e_value",
                "profile_hash", "semantic_run_id", "status", "independence_tier"):
        assert key in exp, key
    assert exp["status"] == "licensed" and exp["independence_tier"] == "reproduced"   # lowercase values
