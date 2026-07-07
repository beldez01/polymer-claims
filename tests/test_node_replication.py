from __future__ import annotations

from polymer_grammar import FDRLedger, IndependenceTier, MaterializationContext, Status
from polymer_protocol import Corpus

from polymer_claims.analysis_profile import profile_oracle_registry
from polymer_claims.capabilities import CAPABILITY_CELLS
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_adapters import (
    RegionHodgesLehmannAdapter,
    RegionMeanDiffAdapter,
    methyl_independent_registry,
    region_delta_beta_claim,
)
from polymer_claims.node import NodeRunner
from polymer_claims.profiles import CANONICAL_EPICV2_V1


def test_node_runner_computes_replication_inputs_live():
    ctx = MaterializationContext(id="M", api_version="v1", data_version="d1")
    claim = region_delta_beta_claim(
        "c-repl-live",
        ref="se:epicv2_casectrl_powered@1",
        region_probes=("cg00000001", "cg00000002", "cg00000003", "cg00000004", "cg00000005"),
    )
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    runner = NodeRunner.from_seed(
        corpus,
        adapters=(RegionMeanDiffAdapter(), RegionHodgesLehmannAdapter()),
        ctx=ctx,
        scheduler_budget=10.0,
        adapter_registry=methyl_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        materializations=materialization_map(corpus, ctx),
        replication_bindings={"c-repl-live": "se:epicv2_casectrl_demo_b@1"},
        layout="force",
        budget=2.5,
        capability_registry=CAPABILITY_CELLS,
    )

    runner.tick()
    licensed = next(c for c in runner.corpus.claims if c.id == "c-repl-live")
    assert licensed.status is Status.LICENSED
    assert licensed.licensing is not None
    assert licensed.licensing.independence_tier is IndependenceTier.REPLICATED
    assert len(licensed.licensing.satisfactions) == 2
