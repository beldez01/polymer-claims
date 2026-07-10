"""HERV-K(HML-2) n-DMP count-enrichment drive: the endogenous-retrovirus node.

Unlike the MHC drive (one contiguous window), HERV-K LTR5_Hs elements are scattered genome-wide, so
CpGs are gathered across MANY small element windows (hervk_ltr5_windows -> extract_cpg_matrix_multi)
into ONE probe matrix, then the same n-DMP count route runs: a multi-probe SE-Contract, an n-DMP count
claim contrasting two lineage groups, pre-registration, and the real e-LOND gate. Two INDEPENDENT legs
(pooled-t + Mann-Whitney rank-sum; ndmp_independent_registry) must each clear the pre-registered floor.

Pre-registered k is reused verbatim from rip_mhc_ndmp.preregistered_k: ceil(3*alpha*N), set from N and
alpha BEFORE any count is observed (never tuned to the observed count).

Umbrella/impure (atlas + rmsk + contract I/O). Grammar/protocol/methyl_ndmp/evidence untouched.
"""
from __future__ import annotations

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
from .ingest.hervk_loci import hervk_ltr5_windows
from .ingest.loyfer_wgbs import extract_cpg_matrix_multi
from .materialization import materialization_map
from .methyl_ndmp import (
    NDmpRankAdapter,
    NDmpTTestAdapter,
    n_dmps_claim,
    ndmp_independent_registry,
)
from .profiles import CANONICAL_EPICV2_V1
from .rip_mhc_ndmp import preregistered_k  # reuse the severe-test count floor (do NOT redefine)

_ADAPTERS = (NDmpTTestAdapter(), NDmpRankAdapter())
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="loyfer_2023@1")


@dataclass
class HervkNdmpResult:
    verdict: str            # "LICENSED" | "REJECTED" | "PENDING"
    status: Status
    n_windows: int          # LTR5_Hs elements gathered
    n_probes: int           # complete-case CpG probes across all windows
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


def run_hervk_ndmp(
    rmsk_path,
    bed_dir,
    manifest,
    contracts_dir,
    *,
    group_col: str = "lineage",
    level_a: str = "Lymphoid",
    level_b: str = "Myeloid",
    alpha: float = 0.05,
    min_cov: int = 4,
    k: int | None = None,
    uid: str = "hervk_ndmp_lym_mye@1",
    target_fdr: float = 0.05,
) -> HervkNdmpResult:
    """Gather CpGs across all HERV-K LTR5_Hs windows into one complete-case matrix, build a multi-probe
    contract, and drive the n-DMP count claim (level_a vs level_b on `group_col`) through the
    pre-registered e-LOND gate. `k` is pre-registered from N and alpha unless the caller pins it.
    """
    contracts_dir = Path(contracts_dir)
    windows = hervk_ltr5_windows(Path(rmsk_path))
    matrix = extract_cpg_matrix_multi(Path(bed_dir), Path(manifest), windows, min_cov=min_cov)
    n_windows = len(windows)
    n_probes = len(matrix.probe_ids)
    if k is None:
        k = preregistered_k(n_probes, alpha)  # set BEFORE any count is observed

    build_cpg_matrix_contract(matrix, uid, contracts_dir, group_col=group_col)

    # Synthetic descriptor: LTR5_Hs is scattered, so there is no single genomic window. The subject
    # records the element class and count, not a contiguous locus.
    claim = n_dmps_claim(
        "hervk-ndmp",
        ref=f"se:{uid}",
        probes=tuple(matrix.probe_ids),
        region=("HERVK_LTR5_Hs", 0, n_windows),
        group_col=group_col,
        level_a=level_a,
        level_b=level_b,
        alpha=alpha,
        k=float(k),
        comparator=Comparator.GE,
        title=f"n-DMPs {level_a} vs {level_b} across {n_windows} HERV-K LTR5_Hs elements",
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

    c = next(x for x in corpus.claims if x.id == "hervk-ndmp")
    t = next((x for x in corpus.fdr_ledger.tests if x.claim_id == "hervk-ndmp"), None)
    e_value = t.e_value if t is not None else None
    slot1_bar = (1.0 / t.alpha_allocated) if (t is not None and t.alpha_allocated) else None

    return HervkNdmpResult(
        verdict=_verdict(c.status), status=c.status, n_windows=n_windows, n_probes=n_probes, k=k,
        count_ttest=count_ttest, count_rank=count_rank,
        e_value=e_value, slot1_bar=slot1_bar, corpus=corpus,
    )
