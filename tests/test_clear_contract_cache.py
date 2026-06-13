from polymer_claims.contracts import _load_contract, clear_contract_cache, load_contract


def test_clear_contract_cache_resets_lru():
    load_contract("se:epicv2_casectrl_demo@1")
    assert _load_contract.cache_info().currsize >= 1
    clear_contract_cache()
    assert _load_contract.cache_info().currsize == 0
    # still works after a clear (re-reads disk)
    assert load_contract("se:epicv2_casectrl_demo@1").dimnames_hash.startswith("sha256:")
