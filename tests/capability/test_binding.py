import pytest
from polymer_claims.capabilities import (
    bind, validate_trust_binding, CapabilityNotFound, CapabilityTrustBinding,
    MEAN_DIFF_CELL, N_DMPS_CELL, EVAL_BENCHMARK_ADVANTAGE_CELL,
)
from polymer_claims.exec_adapters import apparatus_oracle_registry
from polymer_protocol import AdapterRegistry
from polymer_protocol.adapter_registry import AdapterCredential
from polymer_grammar.capability import (
    ConformanceReason as R, ConformanceWarning as W, OracleRequirement,
)
from polymer_grammar.executor_credential import ExecutorTrustEntry, ExecutorTrustRegistry

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


# ---------------------------------------------------------------------------
# Task 16 — regression: existing bindings unbroken by new CapabilityTrustBinding fields
# ---------------------------------------------------------------------------

def test_bind_succeeds_all_three_existing():
    """bind() still works for the three pre-existing cells (new fields have empty defaults)."""
    for cap in ("stats::mean_diff", "methyl::region_delta_beta", "methyl::n_dmps"):
        b = bind(cap, "v1")
        assert isinstance(b, CapabilityTrustBinding)
        # New fields should be empty by default
        assert b.executor_descriptor_registry.descriptors == ()
        assert b.executor_trust_registry.entries == ()


def test_existing_cells_still_require_independent_pair():
    """The three pre-existing recompute-pair cells still fail without an independent pair."""
    reg = AdapterRegistry(credentials=(
        AdapterCredential(identity="stats-pure", owner="same", implementation_hash="sha256:" + "a" * 64, trusted=True),
        AdapterCredential(identity="stats-stdlib", owner="same", implementation_hash="sha256:" + "a" * 64, trusted=True),
    ))  # same owner + same hash → not independent
    res = validate_trust_binding(MEAN_DIFF_CELL, reg, bind("stats::mean_diff").oracle_registry)
    assert R.BINDING_NO_INDEPENDENT_PAIR in res.reasons and not res.ok


# ---------------------------------------------------------------------------
# Task 16 — eval::benchmark_advantage binding
# ---------------------------------------------------------------------------

def test_benchmark_binding_validates_ok():
    """validate_trust_binding for the new cell with its kit registries passes."""
    b = bind("eval::benchmark_advantage", "v1")
    res = validate_trust_binding(
        EVAL_BENCHMARK_ADVANTAGE_CELL,
        b.adapter_registry,
        b.oracle_registry,
        evidence_policy_registry=b.evidence_policy_registry,
        executor_descriptor_registry=b.executor_descriptor_registry,
        executor_trust_registry=b.executor_trust_registry,
    )
    assert res.ok, f"Expected ok but got reasons={res.reasons} warnings={res.warnings}"


def test_benchmark_binding_wrong_predictor_identity():
    """A descriptor whose predictor identity is NOT in eligible_adapter_identities → not ok.

    Approach: keep the kit registries (with predictor identity 'benchmark-model') but give the
    cell a modified eligible_adapter_identities that excludes that identity.  The descriptor
    resolves successfully but its predictor identity is not in the cell's eligible set.
    """
    b = bind("eval::benchmark_advantage", "v1")
    # Override the cell's eligible_adapter_identities to exclude "benchmark-model"
    bad_cell = EVAL_BENCHMARK_ADVANTAGE_CELL.model_copy(update={
        "eligible_adapter_identities": ("some-other-identity",),
    })
    res = validate_trust_binding(
        bad_cell,
        b.adapter_registry,
        b.oracle_registry,
        evidence_policy_registry=b.evidence_policy_registry,
        executor_descriptor_registry=b.executor_descriptor_registry,
        executor_trust_registry=b.executor_trust_registry,
    )
    assert not res.ok, "Expected NOT ok for wrong predictor identity"


def test_benchmark_binding_untrusted_executor():
    """An untrusted ExecutorTrustEntry → not ok."""
    b = bind("eval::benchmark_advantage", "v1")
    # Pull the descriptor hash from the binding's descriptor registry
    descriptor_hash = b.executor_descriptor_registry.descriptors[0].content_hash

    # Replace the trust registry with one containing an untrusted entry for the same descriptor
    untrusted_entry = ExecutorTrustEntry(
        descriptor_ref=descriptor_hash,
        owner="polymer-claims-v1",
        trusted=False,  # explicitly NOT trusted
        version="v1",
    )
    bad_trust_registry = ExecutorTrustRegistry(entries=(untrusted_entry,))

    res = validate_trust_binding(
        EVAL_BENCHMARK_ADVANTAGE_CELL,
        b.adapter_registry,
        b.oracle_registry,
        evidence_policy_registry=b.evidence_policy_registry,
        executor_descriptor_registry=b.executor_descriptor_registry,
        executor_trust_registry=bad_trust_registry,
    )
    assert not res.ok, "Expected NOT ok for untrusted executor entry"
