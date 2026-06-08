from polymer_grammar import (
    Comparator,
    DataHandle,
    FDRLedger,
    MaterializationContext,
    MeasurementBasis,
    OperationNode,
    ProducedLeafSpec,
    Status,
)
from polymer_protocol import AdapterCredential, AdapterRegistry, Corpus, run_cycle

from polymer_claims.datasets import load_dataset
from polymer_claims.exec_adapters import (
    StatsPureAdapter,
    StatsStdlibAdapter,
    independent_registry,
    mean_diff_claim,
)

_CTX = MaterializationContext(id="M1", api_version="v1", data_version="dose_response@v1")


def _mean_diff_node(value_col="response", group_col="dose", group_a="high", group_b="low", ref="dose_response"):
    return OperationNode(
        id="n0",
        impl="stats::mean_diff",
        inputs=(DataHandle(ref=ref),),
        params=(
            ("value_col", value_col),
            ("group_col", group_col),
            ("group_a", group_a),
            ("group_b", group_b),
        ),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def test_both_adapters_compute_the_same_mean_diff():
    node = _mean_diff_node()
    pure = StatsPureAdapter().execute(node, (), _CTX).value
    stdlib = StatsStdlibAdapter().execute(node, (), _CTX).value
    assert pure == stdlib
    assert abs(pure - 14.0) < 1e-9


def test_adapter_identities_are_distinct():
    assert StatsPureAdapter().identity == "stats-pure"
    assert StatsStdlibAdapter().identity == "stats-stdlib"
    assert StatsPureAdapter().identity != StatsStdlibAdapter().identity


def test_bad_column_raises_inside_adapter():
    import pytest
    node = _mean_diff_node(value_col="__missing__")
    with pytest.raises(Exception):
        StatsPureAdapter().execute(node, (), _CTX)


def test_unsupported_impl_raises():
    import pytest
    bad = OperationNode(
        id="n0", impl="builtin::const", params=(("value", "1"),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    with pytest.raises(Exception):
        StatsStdlibAdapter().execute(bad, (), _CTX)


def test_load_dataset_returns_columns():
    data = load_dataset("dose_response")
    assert data["dose"][:2] == ["high", "high"]
    assert data["response"][0] == "30"
    assert len(data["response"]) == 12
    assert set(data["dose"]) == {"high", "low"}


def test_load_dataset_unknown_ref_raises():
    import pytest
    with pytest.raises(Exception):
        load_dataset("__nope__")


# ---------------------------------------------------------------------------
# Task 3 — plan-builder + end-to-end integration through run_cycle
# ---------------------------------------------------------------------------
_ADAPTERS = (StatsPureAdapter(), StatsStdlibAdapter())


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


def _status(result, claim_id):
    return next(c.status for c in result.corpus.claims if c.id == claim_id)


def test_true_claim_licenses_on_computed_value():
    c = mean_diff_claim("c-true", comparator=Comparator.GT, threshold=10.0)
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX, adapter_registry=independent_registry())
    assert _status(result, "c-true") == Status.LICENSED


def test_false_claim_is_rejected_on_computed_value():
    c = mean_diff_claim("c-false", comparator=Comparator.GT, threshold=20.0)
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX, adapter_registry=independent_registry())
    assert _status(result, "c-false") == Status.REJECTED


def test_same_owner_pair_is_held_pending_by_independence_gate():
    c = mean_diff_claim("c-dep", comparator=Comparator.GT, threshold=10.0)
    same_owner = AdapterRegistry(credentials=(
        AdapterCredential(identity="stats-pure", owner="same", implementation_hash="h-pure"),
        AdapterCredential(identity="stats-stdlib", owner="same", implementation_hash="h-stdlib"),
    ))
    result = run_cycle(_corpus(c), _ADAPTERS, _CTX, adapter_registry=same_owner)
    assert _status(result, "c-dep") == Status.PENDING
