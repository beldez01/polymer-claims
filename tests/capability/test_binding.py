import pytest
from polymer_claims.capabilities import (
    bind, validate_trust_binding, CapabilityNotFound, CapabilityTrustBinding,
    MEAN_DIFF_CELL, N_DMPS_CELL,
)
from polymer_claims.exec_adapters import apparatus_oracle_registry
from polymer_protocol import AdapterRegistry
from polymer_protocol.adapter_registry import AdapterCredential
from polymer_grammar.capability import (
    ConformanceReason as R, ConformanceWarning as W, OracleRequirement,
)

def test_bind_resolves_each():
    for cap in ("stats::mean_diff", "methyl::region_delta_beta", "methyl::n_dmps"):
        b = bind(cap, "v1")
        assert isinstance(b, CapabilityTrustBinding) and b.trust_profile

def test_bind_unknown_raises():
    with pytest.raises(CapabilityNotFound):
        bind("nope", "v1")
    with pytest.raises(CapabilityNotFound):
        bind("stats::mean_diff", "v9")

def test_valid_binding_passes():
    b = bind("stats::mean_diff", "v1")
    assert validate_trust_binding(MEAN_DIFF_CELL, b.adapter_registry, b.oracle_registry).ok

def test_methyl_cell_with_apparatus_oracle_registry_fails():
    b = bind("methyl::n_dmps", "v1")
    res = validate_trust_binding(N_DMPS_CELL, b.adapter_registry, apparatus_oracle_registry())
    assert R.BINDING_ORACLE_MISSING in res.reasons and not res.ok

def test_missing_eligible_is_dedup_warning_not_failure():
    cell = MEAN_DIFF_CELL.model_copy(update={
        "eligible_adapter_identities": ("stats-pure", "stats-stdlib", "ghost")})
    b = bind("stats::mean_diff", "v1")
    res = validate_trust_binding(cell, b.adapter_registry, b.oracle_registry)
    assert res.ok and res.warnings.count(W.BINDING_ADAPTER_MISSING) == 1  # deduped

def test_trust_binding_requires_nonempty_profile():
    b = bind("stats::mean_diff")
    with pytest.raises(ValueError):
        CapabilityTrustBinding(adapter_registry=b.adapter_registry,
                               oracle_registry=b.oracle_registry, trust_profile="  ")

def test_untrusted_eligible_is_dedup_warning():
    reg = AdapterRegistry(credentials=(
        AdapterCredential(identity="stats-pure", owner="o1", implementation_hash="h1", trusted=True),
        AdapterCredential(identity="stats-stdlib", owner="o2", implementation_hash="h2", trusted=True),
        AdapterCredential(identity="bad", owner="o3", implementation_hash="h3", trusted=False),
    ))
    cell = MEAN_DIFF_CELL.model_copy(update={
        "eligible_adapter_identities": ("stats-pure", "stats-stdlib", "bad", "bad2")})
    res = validate_trust_binding(cell, reg, bind("stats::mean_diff").oracle_registry)
    assert res.ok  # a trusted independent pair still exists
    assert res.warnings.count(W.BINDING_ADAPTER_UNTRUSTED) == 1   # "bad", deduped
    assert res.warnings.count(W.BINDING_ADAPTER_MISSING) == 1     # "bad2", deduped

def test_no_independent_pair_is_fatal():
    reg = AdapterRegistry(credentials=(
        AdapterCredential(identity="stats-pure", owner="same", implementation_hash="h", trusted=True),
        AdapterCredential(identity="stats-stdlib", owner="same", implementation_hash="h", trusted=True),
    ))  # same owner + same hash → not independent
    res = validate_trust_binding(MEAN_DIFF_CELL, reg, bind("stats::mean_diff").oracle_registry)
    assert R.BINDING_NO_INDEPENDENT_PAIR in res.reasons and not res.ok

def test_required_oracle_without_default_is_unknown_warning():
    cell = MEAN_DIFF_CELL.model_copy(update={"oracle": OracleRequirement(required=True)})  # no default
    b = bind("stats::mean_diff")
    res = validate_trust_binding(cell, b.adapter_registry, b.oracle_registry)
    assert res.ok and W.BINDING_ORACLE_SATISFIABILITY_UNKNOWN in res.warnings

def test_methyl_binding_resolves_profile_oracle():
    b = bind("methyl::n_dmps", "v1")
    assert validate_trust_binding(N_DMPS_CELL, b.adapter_registry, b.oracle_registry).ok
    assert b.trust_profile == "bundled-recomputable-public"
