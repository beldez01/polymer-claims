"""The shared n-DMP gate construction used by BOTH kernel proofs (synthetic + real).

Builds the fixed n-DMP claim (spec §4.4) over a contract `ref`, runs the REAL gate via run_cycle,
and returns the observed quantities. The caller owns the contract-root scoping (the synthetic proof
builds into a temp root; the real proof runs under the pinned root). Deterministic; no network.
"""
from __future__ import annotations

import math

from polymer_grammar import FDRLedger, MaterializationContext
from polymer_protocol import Corpus, run_cycle

from .analysis_profile import profile_oracle_id, profile_oracle_registry
from .evidence import count_enrichment_evalue
from .materialization import materialization_map
from .methyl_ndmp import (
    NDmpOlsCoefAdapter,
    NDmpTTestAdapter,
    _all_probe_ids,
    dmp_indicators,
    n_dmps_claim,
    ndmp_independent_registry,
)
from .profiles import CANONICAL_HM450_V1


def run_ndmp_gate(ref: str, claim_id: str, *, alpha: float = 0.05) -> dict:
    """Build the fixed n-DMP claim over `ref` and run the real gate, scoped to the active contract
    root. Returns the observed gate quantities (probes default to ALL via probes=None)."""
    n_probes = len(_all_probe_ids(ref))
    k = math.ceil(alpha * n_probes)
    claim = n_dmps_claim(
        claim_id, ref=ref, group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
        alpha=alpha, k=k, oracle_ref=profile_oracle_id(CANONICAL_HM450_V1))
    node = claim.evaluation_plan.graph.nodes[0]
    ind = dmp_indicators(node)
    n_dmps = int(sum(ind))
    evalue = count_enrichment_evalue(ind, p0=alpha)
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    result = run_cycle(
        corpus, (NDmpTTestAdapter(), NDmpOlsCoefAdapter()), base,
        adapter_registry=ndmp_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_HM450_V1, "recomputable_public")),
        materializations=materialization_map(corpus, base, profiles=(CANONICAL_HM450_V1,)),
        evidence={claim_id: evalue})
    c = next((x for x in result.corpus.claims if x.id == claim_id), None)
    if c is None:
        raise RuntimeError(f"claim {claim_id!r} missing from cycle result")
    tier = c.licensing.independence_tier if c.licensing is not None else None
    profile_hash = semantic_run_id = None
    if c.licensing is not None and c.licensing.satisfactions:
        m = c.licensing.satisfactions[0].materialization
        profile_hash, semantic_run_id = m.profile_hash, m.semantic_run_id
    return {
        "n_probes": n_probes, "k": k, "n_dmps": n_dmps, "e_value": evalue,
        "status_enum": c.status, "tier_enum": tier,
        "status": c.status.value, "independence_tier": tier.value if tier is not None else None,
        "profile_hash": profile_hash, "semantic_run_id": semantic_run_id,
    }
