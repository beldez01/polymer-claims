"""The 2c reconciliation, end-to-end on the bundled real-data seed: a None-strength + oracle_ref
mean_diff claim now licenses by EARNING its strength from the computed mean difference (off the
exempt scaffolding), tier-capped by the BENCHMARKED apparatus oracle."""
from polymer_grammar import MaterializationContext, Status

from polymer_claims.exec_adapters import (
    apparatus_oracle_registry,
    independent_registry,
    real_data_seed_corpus,
)
from polymer_protocol import run_cycle
from polymer_protocol.cost import CostModel

# mirror the real call site (src/polymer_claims/node.py `_CTX`)
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="d1")


def _adapters():
    from polymer_claims.exec_adapters import StatsPureAdapter, StatsStdlibAdapter
    return (StatsPureAdapter(), StatsStdlibAdapter())


def test_seed_claim_licenses_with_earned_capped_strength():
    corpus, kwargs = real_data_seed_corpus()
    out = run_cycle(
        corpus,
        _adapters(),
        _CTX,
        oracles=apparatus_oracle_registry(),
        adapter_registry=independent_registry(),
        cost_model=CostModel(),
        **kwargs,
    )
    graded = out.corpus.by_id()
    md1 = graded["seed-md-1"]
    # the true high-low diff is 14.0; threshold 10.0 (GT) -> strong margin -> earns + licenses
    assert md1.status == Status.LICENSED
    assert md1.strength is not None                      # EARNED (builder default was None)
    assert md1.strength.evidence_against_null <= 0.6     # capped by BENCHMARKED
    assert md1.strength.magnitude <= 0.6
    assert md1.strength.severity == 0.7                  # theory axis uncapped
    # seed-md-2 wants >20 over a true 14 -> refuted -> rejected (not earned)
    assert graded["seed-md-2"].status == Status.REJECTED
