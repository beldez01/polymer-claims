from __future__ import annotations

from polymer_grammar import FDRLedger, IndependenceTier, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.capabilities import CAPABILITY_CELLS
from polymer_claims.evidence import evidence_map
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_adapters import (
    RegionHodgesLehmannAdapter, RegionMeanDiffAdapter, methyl_independent_registry, region_delta_beta_claim,
)
from polymer_claims.profiles import CANONICAL_EPICV2_V1
from polymer_claims.replication import build_replication_inputs

_ADAPTERS = (RegionMeanDiffAdapter(), RegionHodgesLehmannAdapter())
_BASE = MaterializationContext(id="M", api_version="v1", data_version="d1")
_POWERED = "se:epicv2_casectrl_powered@1"
_STRONG = ("cg00000001", "cg00000002", "cg00000003", "cg00000004", "cg00000005")
_REF_B = "se:epicv2_casectrl_demo_b@1"


def _corpus(claim):
    return Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_replicated_across_two_cohorts_licenses_at_replicated_tier():
    # cohort A = powered strong region (already clears the e-gate single-cohort);
    # cohort B = demo_b@1 (distinct cohort, same cg1-5 signal proposition, n=100)
    claim = region_delta_beta_claim("c-repl", ref=_POWERED, region_probes=_STRONG)
    corpus = _corpus(claim)
    rep = build_replication_inputs(corpus, _BASE, bindings={"c-repl": _REF_B})

    result = run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=methyl_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE),
        evidence=rep.evidence,
        replications=rep.replications,
        capability_registry=CAPABILITY_CELLS,
    )
    c = next(x for x in result.corpus.claims if x.id == "c-repl")
    assert c.status == Status.LICENSED
    assert c.licensing.independence_tier is IndependenceTier.REPLICATED
    assert c.licensing.shared_cause_overlap == 0.2
    # two satisfactions across two distinct cohorts
    cohorts = {s.materialization.dimnames_hash for s in c.licensing.satisfactions}
    assert len(cohorts) == 2
    # ONE e-LOND test/discovery (the product is one test, not two)
    assert result.corpus.fdr_ledger.n_tests == 1
    assert result.corpus.fdr_ledger.n_discoveries == 1


def test_single_cohort_demo_stays_reproduced():
    claim = region_delta_beta_claim("c-solo", ref=_POWERED, region_probes=_STRONG)  # cohort A only
    corpus = _corpus(claim)
    result = run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=methyl_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE),
        evidence=evidence_map(corpus),
        capability_registry=CAPABILITY_CELLS,
    )
    c = next(x for x in result.corpus.claims if x.id == "c-solo")
    assert c.status == Status.LICENSED
    assert c.licensing.independence_tier is IndependenceTier.REPRODUCED
    assert len(c.licensing.satisfactions) == 1


def test_same_cohort_binding_does_not_multiply_or_replicate():
    claim = region_delta_beta_claim("c-same", ref=_POWERED, region_probes=_STRONG)
    corpus = _corpus(claim)
    rep = build_replication_inputs(corpus, _BASE, bindings={"c-same": _POWERED})
    result = run_cycle(
        corpus, _ADAPTERS, _BASE,
        adapter_registry=methyl_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, _BASE),
        evidence=rep.evidence,
        replications=rep.replications,
        capability_registry=CAPABILITY_CELLS,
    )
    c = next(x for x in result.corpus.claims if x.id == "c-same")
    assert c.status == Status.LICENSED
    assert c.licensing.independence_tier is IndependenceTier.REPRODUCED
    assert len(c.licensing.satisfactions) == 1
