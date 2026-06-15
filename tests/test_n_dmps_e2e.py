from __future__ import annotations

from polymer_grammar import FDRLedger, IndependenceTier, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.evidence import evidence_map
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_ndmp import NDmpOlsCoefAdapter, NDmpTTestAdapter, n_dmps_claim, ndmp_independent_registry
from polymer_claims.profiles import CANONICAL_EPICV2_V1

_ADAPTERS = (NDmpTTestAdapter(), NDmpOlsCoefAdapter())
_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")
_NULL_PROBES = tuple(f"cg{i:08d}" for i in range(11, 25))  # control region only (no signal)


def _run(claim):
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    return run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=ndmp_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE),
        evidence=evidence_map(corpus),
    )


def test_n_dmps_over_signal_licenses_reproduced():
    claim = n_dmps_claim("c-ndmp", ref="se:epicv2_casectrl_powered@1", k=3)  # all 24 probes
    result = _run(claim)
    c = next(x for x in result.corpus.claims if x.id == "c-ndmp")
    assert c.status == Status.LICENSED
    assert c.licensing.independence_tier is IndependenceTier.REPRODUCED
    assert result.corpus.fdr_ledger.n_discoveries == 1


def test_n_dmps_over_null_region_does_not_license():
    # THE MONEY-SHOT: only control probes -> count ~ alpha*M (chance) < k=3 -> not licensed.
    claim = n_dmps_claim("c-null", ref="se:epicv2_casectrl_powered@1", probes=_NULL_PROBES, k=3)
    result = _run(claim)
    c = next(x for x in result.corpus.claims if x.id == "c-null")
    assert c.status != Status.LICENSED


def test_same_owner_pair_held_pending():
    from polymer_protocol import AdapterCredential, AdapterRegistry
    same_owner = AdapterRegistry(credentials=(
        AdapterCredential(identity="methyl-ndmp-ttest", owner="o", implementation_hash="h1"),
        AdapterCredential(identity="methyl-ndmp-ols", owner="o", implementation_hash="h2"),
    ))
    claim = n_dmps_claim("c-ndmp", ref="se:epicv2_casectrl_powered@1", k=3)
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    result = run_cycle(
        corpus, _ADAPTERS, _BASE, adapter_registry=same_owner,
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE), evidence=evidence_map(corpus),
    )
    c = next(x for x in result.corpus.claims if x.id == "c-ndmp")
    assert c.status != Status.LICENSED  # air-gap: same owner -> not registry-independent
