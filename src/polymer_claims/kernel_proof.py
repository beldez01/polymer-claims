"""Offline kernel proof: build the synthetic HM450 fixture, run the REAL n-DMP gate, return the
outcome. Shared by the verify-kernel CLI and the CI guard test. No network; deterministic.
Builds into a TemporaryDirectory scoped by using_contract_root — nothing is written to the source
tree. See docs/superpowers/specs/2026-06-23-offline-kernel-proof-design.md."""
from __future__ import annotations

import math
import tempfile
from dataclasses import dataclass
from pathlib import Path

from polymer_grammar import FDRLedger, MaterializationContext, Status
from polymer_protocol import Corpus, run_cycle

from polymer_claims.analysis_profile import profile_oracle_id, profile_oracle_registry
from polymer_claims.contracts import clear_contract_cache, using_contract_root
from polymer_claims.evidence import count_enrichment_evalue
from polymer_claims.ingest.synthetic import build_synthetic_contract
from polymer_claims.materialization import materialization_map
from polymer_claims.methyl_ndmp import (
    NDmpOlsCoefAdapter,
    NDmpTTestAdapter,
    _all_probe_ids,
    dmp_indicators,
    n_dmps_claim,
    ndmp_independent_registry,
)
from polymer_claims.profiles import CANONICAL_HM450_V1

_REF = "se:tcga_laml_idh_synth@1"
_ALPHA = 0.05
_CLAIM_ID = "synthetic-kernel-ndmp"


@dataclass(frozen=True)
class KernelProofResult:
    status: Status
    independence_tier: object | None   # IndependenceTier | None — kept loose to avoid import coupling
    n_dmps: int
    e_value: float
    n_probes: int
    k: int
    licensed: bool


def run_synthetic_kernel_proof() -> KernelProofResult:
    """Build the synthetic contract into a temp dir, run the real gate scoped to it, return result.
    Writes nothing to the source tree; the temp contract is discarded on exit."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build_synthetic_contract(root)
        with using_contract_root(root):
            clear_contract_cache()   # don't resolve a stale cached entry for this uid
            n_probes = len(_all_probe_ids(_REF))
            k = math.ceil(_ALPHA * n_probes)
            claim = n_dmps_claim(
                _CLAIM_ID, ref=_REF,
                group_col="Sample_Group", level_a="WT", level_b="IDH_mut",
                alpha=_ALPHA, k=k, oracle_ref=profile_oracle_id(CANONICAL_HM450_V1),
            )
            node = claim.evaluation_plan.graph.nodes[0]
            ind = dmp_indicators(node)
            n_dmps = int(sum(ind))
            evalue = count_enrichment_evalue(ind, p0=_ALPHA)

            base = MaterializationContext(id="M", api_version="v1", data_version="d1")
            corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
            result = run_cycle(
                corpus, (NDmpTTestAdapter(), NDmpOlsCoefAdapter()), base,
                adapter_registry=ndmp_independent_registry(),
                oracles=profile_oracle_registry((CANONICAL_HM450_V1, "recomputable_public")),
                materializations=materialization_map(corpus, base, profiles=(CANONICAL_HM450_V1,)),
                evidence={_CLAIM_ID: evalue},
            )
            c = next(x for x in result.corpus.claims if x.id == _CLAIM_ID)
            tier = c.licensing.independence_tier if c.licensing is not None else None
        clear_contract_cache()   # leave no temp-rooted cache entry behind
    return KernelProofResult(
        status=c.status, independence_tier=tier, n_dmps=n_dmps, e_value=evalue,
        n_probes=n_probes, k=k, licensed=(c.status is Status.LICENSED),
    )
