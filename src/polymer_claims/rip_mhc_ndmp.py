"""MHC n-DMP count-enrichment drive: extract a per-CpG x per-sample matrix over a genomic window
(M1's extract_cpg_matrix), write a multi-probe SE-Contract, build an n-DMP count claim contrasting
two lineage groups, pre-register it, and run it through the real e-LOND gate.

Unlike the region-Δβ drive (one scalar per region -> e-value ~1 over the MHC), the count e-value
(evidence.count_enrichment_evalue) accumulates Bernoulli DMP-indicators across THOUSANDS of probes,
so a genuine lineage contrast can clear the shallow slot-1 e-LOND bar. Two INDEPENDENT legs
(pooled-t + Mann-Whitney rank-sum; ndmp_independent_registry) must each clear the pre-registered
count floor `k`.

Pre-registered k (the severe-test effect floor): set BEFORE seeing the observed count as a multiple
of the chance rate. At per-probe alpha the null expected DMP count is alpha*N; k = ceil(3*alpha*N)
requires >=3x the chance rate. The count e-value does the FDR work; k is the effect floor.

Umbrella/impure (atlas + contract I/O). Grammar/protocol/methyl_ndmp/evidence untouched.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from polymer_grammar import Comparator, FDRLedger, MaterializationContext, Status, register_test
from polymer_grammar.commitment import commitment_hash
from polymer_protocol import Corpus, run_cycle

from .analysis_profile import profile_oracle_registry
from .capabilities import CAPABILITY_CELLS
from .contracts import clear_contract_cache, using_contract_root
from .evidence import evidence_map
from .ingest.build_cpg_matrix_contract import build_cpg_matrix_contract
from .ingest.loyfer_wgbs import extract_cpg_matrix
from .materialization import materialization_map
from .methyl_ndmp import (
    NDmpRankAdapter,
    NDmpTTestAdapter,
    n_dmps_claim,
    ndmp_independent_registry,
)
from .profiles import CANONICAL_EPICV2_V1

_ADAPTERS = (NDmpTTestAdapter(), NDmpRankAdapter())
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="loyfer_2023@1")


def preregistered_k(n_probes: int, alpha: float) -> int:
    """The severe-test count floor, set from N and alpha ONLY (never the observed count):
    3x the null chance rate, ceil(3 * alpha * N). >=1 so a claim always has a nontrivial floor."""
    return max(1, math.ceil(3.0 * alpha * n_probes))


@dataclass
class MhcNdmpResult:
    verdict: str            # "LICENSED" | "REJECTED" | "PENDING"
    status: Status
    n_probes: int
    k: int
    count_ttest: int        # leg A observed DMP count
    count_rank: int         # leg B observed DMP count
    e_value: float | None   # count-enrichment e-value recorded at the pre-registered slot
    slot1_bar: float | None  # 1 / alpha_allocated at slot 1 (the e-LOND bar the e-value must clear)
    corpus: object


def _verdict(status) -> str:
    if status == Status.LICENSED:
        return "LICENSED"
    if status == Status.REJECTED:
        return "REJECTED"
    return "PENDING"


def run_mhc_ndmp(
    bed_dir,
    manifest,
    contracts_dir,
    *,
    chrom: str,
    start: int,
    end: int,
    group_col: str = "lineage",
    level_a: str = "Lymphoid",
    level_b: str = "Myeloid",
    alpha: float = 0.05,
    min_cov: int = 4,
    k: int | None = None,
    uid: str = "mhc_ndmp_lym_mye@1",
    target_fdr: float = 0.05,
) -> MhcNdmpResult:
    """Extract the complete-case CpG matrix over [start,end), build a multi-probe contract, and drive
    the n-DMP count claim (level_a vs level_b on `group_col`) through the pre-registered e-LOND gate.

    `k` is pre-registered from N and alpha (preregistered_k) unless the caller pins it. Returns a
    MhcNdmpResult with both legs' observed counts, the count e-value, the slot-1 bar, and the verdict.
    """
    contracts_dir = Path(contracts_dir)
    matrix = extract_cpg_matrix(
        Path(bed_dir), Path(manifest), chrom, start, end,
        min_cov=min_cov, require_all_samples=True,
    )
    n_probes = len(matrix.probe_ids)
    if k is None:
        k = preregistered_k(n_probes, alpha)  # set BEFORE any count is observed

    build_cpg_matrix_contract(matrix, uid, contracts_dir, group_col=group_col)

    # Pass probes explicitly (matrix order) so claim construction does not depend on the scoped root.
    claim = n_dmps_claim(
        "mhc-ndmp",
        ref=f"se:{uid}",
        probes=tuple(matrix.probe_ids),
        region=(chrom, start, end),
        group_col=group_col,
        level_a=level_a,
        level_b=level_b,
        alpha=alpha,
        k=float(k),
        comparator=Comparator.GE,
        title=f"n-DMPs {level_a} vs {level_b} over {chrom}:{start:,}-{end:,}",
    )

    # Pre-registration: charge the e-LOND slot BEFORE execution (commit-before-data).
    ledger = register_test(FDRLedger(target_fdr=target_fdr), claim.id, commitment_hash(claim))
    corpus = Corpus(claims=(claim,), fdr_ledger=ledger)

    oracles = profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public"))
    registry = ndmp_independent_registry()

    count_ttest = count_rank = 0
    with using_contract_root(contracts_dir):
        clear_contract_cache()
        try:
            node = claim.evaluation_plan.graph.nodes[0]
            count_ttest = int(NDmpTTestAdapter().execute(node, (), _CTX).value)
            count_rank = int(NDmpRankAdapter().execute(node, (), _CTX).value)
            result = run_cycle(
                corpus, _ADAPTERS, _CTX,
                adapter_registry=registry,
                oracles=oracles,
                materializations=materialization_map(corpus, _CTX),
                evidence=evidence_map(corpus),
                capability_registry=CAPABILITY_CELLS,
            )
            corpus = result.corpus
        finally:
            clear_contract_cache()

    c = next(x for x in corpus.claims if x.id == "mhc-ndmp")
    t = next((x for x in corpus.fdr_ledger.tests if x.claim_id == "mhc-ndmp"), None)
    e_value = t.e_value if t is not None else None
    slot1_bar = (1.0 / t.alpha_allocated) if (t is not None and t.alpha_allocated) else None

    return MhcNdmpResult(
        verdict=_verdict(c.status), status=c.status, n_probes=n_probes, k=k,
        count_ttest=count_ttest, count_rank=count_rank,
        e_value=e_value, slot1_bar=slot1_bar, corpus=corpus,
    )
