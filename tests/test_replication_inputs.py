from __future__ import annotations

from polymer_claims.contracts import load_contract


def test_cohort_b_resolves_with_distinct_dimnames():
    a = load_contract("se:epicv2_casectrl_demo@1")
    b = load_contract("se:epicv2_casectrl_demo_b@1")
    assert b.contract_uid == "epicv2_casectrl_demo_b@1"
    assert b.dimnames_hash != a.dimnames_hash  # different cohort -> different content-address
