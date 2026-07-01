"""Phase 2: a MIGRATED claim earns LICENSED on real data.

`hla_t_naive_promoter_methylation_bimodal`, re-expressed as an executable two-group mean difference
(CD4-T vs monocyte HLA-A 5'UTR/promoter methylation — real BLUEPRINT WGBS betas in
datasets/hla_a_promoter_meth.csv), clears its threshold via the mean_diff air-gap → LICENSED @
REPRODUCED. Nothing is fabricated: the betas are per-CpG means extracted from real BLUEPRINT
methylation-call bigWigs (chr6:29,940,000-29,944,000, GRCh38).
"""
from polymer_grammar import FDRLedger, MaterializationContext
from polymer_grammar.claim import Status
from polymer_grammar.licensing import IndependenceTier
from polymer_protocol import Corpus, run_cycle

from polymer_claims.exec_adapters import (
    StatsPureAdapter,
    StatsStdlibAdapter,
    apparatus_oracle_registry,
    hla_promoter_meth_claim,
    independent_registry,
)

_ADAPTERS = (StatsPureAdapter(), StatsStdlibAdapter())
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="blueprint_wgbs@2016")


def test_migrated_hla_claim_licenses_on_real_blueprint_methylation():
    c = hla_promoter_meth_claim()
    result = run_cycle(
        Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05)),
        _ADAPTERS,
        _CTX,
        adapter_registry=independent_registry(),
        oracles=apparatus_oracle_registry(),
    )
    out = next(x for x in result.corpus.claims if x.id == c.id)
    assert out.status == Status.LICENSED
    assert out.licensing.independence_tier == IndependenceTier.REPRODUCED
    # both independent adapters agreed on the cell-type mean difference
    assert out.licensing.satisfactions[0].credential_ids == ("stats-pure", "stats-stdlib")
