"""Transposable-element BACKGROUND-ENRICHMENT sweep — the honest recast of the n-DMP TE strain.

The n-DMP sweep (`te_ndmp.run_te_family_sweep`) licenses a family when it has more lineage-DMPs than
CHANCE (k = 3*alpha*N). That is almost always true when two deeply-divergent lineages are compared, so
the matched-background control found every young TE family AT-OR-BELOW the genome-wide lineage-DMP rate
(most DEPLETED; HERV-K alone ~baseline). This module formalizes that control into a first-class claim:
each family's per-probe lineage-DMP rate is tested against a PRE-REGISTERED matched-genomic-background
rate (`bg_rate_ttest`/`bg_rate_rank`, from random windows blind to the families). A family licenses iff
its rate clears the background on BOTH legs (fold>=1) AND the count e-value with p0=background clears the
e-LOND bar — so a license means ENRICHED above baseline, not merely differentially methylated.

Pre-registration integrity mirrors the n-DMP sweep: PANEL order (from `te_ndmp.PANEL`) locks each slot's
alpha_t before any atlas byte is read; the background rates are computed from RANDOM windows, independent
of any family, so they are legitimate pre-registered floors (`estimate_background_dmp_rates`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from polymer_grammar import Comparator, FDRLedger, MaterializationContext, Status, register_test
from polymer_grammar.commitment import commitment_hash
from polymer_protocol import Corpus, run_cycle

from .analysis_profile import profile_oracle_registry
from .background_enrichment import (
    EnrichmentRankAdapter,
    EnrichmentTTestAdapter,
    background_enrichment_claim,
    enrichment_independent_registry,
)
from .capabilities import CAPABILITY_CELLS
from .contracts import clear_contract_cache, using_contract_root
from .evidence import evidence_map
from .ingest.build_cpg_matrix_contract import build_cpg_matrix_contract
from .ingest.loyfer_wgbs import extract_cpg_matrices_multi_families
from .ingest.te_loci import te_family_windows_multi
from .materialization import materialization_map
from .methyl_ndmp import NDmpRankAdapter, NDmpTTestAdapter, n_dmps_claim
from .profiles import CANONICAL_EPICV2_V1
from .te_ndmp import PANEL, EXCLUDED, TeFamilySpec

_ENRICH_ADAPTERS = (EnrichmentTTestAdapter(), EnrichmentRankAdapter())
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="loyfer_2023@1")


def estimate_background_dmp_rates(
    bed_dir,
    manifest,
    contracts_dir,
    *,
    windows_by_rep,
    group_col: str = "lineage",
    level_a: str = "Lymphoid",
    level_b: str = "Myeloid",
    min_cov: int = 4,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """The matched-background per-probe lineage-DMP rate for each leg, pooled over the supplied random
    windows. `windows_by_rep` maps a replicate key -> its list of (chrom, start, end) windows (drawn by
    the caller via `ingest.te_loci.random_background_windows`, independent of any TE family). Returns
    (t_leg_rate, rank_leg_rate) = total DMPs / total complete-case probes across all replicates."""
    contracts_dir = Path(contracts_dir)
    matrices = extract_cpg_matrices_multi_families(
        Path(bed_dir), Path(manifest), windows_by_rep, min_cov=min_cov)
    tot_n = tot_t = tot_r = 0
    with using_contract_root(contracts_dir):
        clear_contract_cache()
        try:
            for key, m in matrices.items():
                n = len(m.probe_ids)
                if not n:
                    continue
                uid = f"te_bg_{key}@1".lower()
                build_cpg_matrix_contract(m, uid, contracts_dir, group_col=group_col)
                claim = n_dmps_claim(
                    f"bg-{uid}", ref=f"se:{uid}", probes=tuple(m.probe_ids),
                    group_col=group_col, level_a=level_a, level_b=level_b,
                    alpha=alpha, k=1.0, comparator=Comparator.GE)
                node = claim.evaluation_plan.graph.nodes[0]
                tot_t += int(NDmpTTestAdapter().execute(node, (), _CTX).value)
                tot_r += int(NDmpRankAdapter().execute(node, (), _CTX).value)
                tot_n += n
        finally:
            clear_contract_cache()
    if tot_n == 0:
        raise ValueError("no complete-case background probes")
    return tot_t / tot_n, tot_r / tot_n


@dataclass
class TeEnrichmentResult:
    key: str
    label: str
    verdict: str                    # "LICENSED" | "REJECTED" | "PENDING"
    status: Status
    n_windows: int
    n_probes: int
    count_ttest: int                # raw leg-A DMP count (would license under the n-DMP chance null)
    count_rank: int                 # raw leg-B DMP count
    fold_ttest: float               # leg-A DMP rate / matched-background t-leg rate
    fold_rank: float                # leg-B DMP rate / matched-background rank-leg rate
    e_value: float | None           # count e-value at p0=background, this family's pre-registered slot
    alpha_allocated: float | None
    bar: float | None


@dataclass
class TeEnrichmentSweepResult:
    families: list[TeEnrichmentResult] = field(default_factory=list)
    corpus: object = None
    bg_rate_ttest: float = 0.0
    bg_rate_rank: float = 0.0
    excluded: tuple[tuple[str, str], ...] = EXCLUDED


def _verdict(status) -> str:
    if status == Status.LICENSED:
        return "LICENSED"
    if status == Status.REJECTED:
        return "REJECTED"
    return "PENDING"


def _build_family_enrichment_claim(spec, matrix, n_windows, contracts_dir, *, group_col, level_a,
                                   level_b, alpha, bg_rate_ttest, bg_rate_rank):
    n_probes = len(matrix.probe_ids)
    uid = f"te_{spec.key}_enrich_{level_a}_{level_b}@1".lower()
    build_cpg_matrix_contract(matrix, uid, contracts_dir, group_col=group_col)
    claim = background_enrichment_claim(
        f"te-{spec.key}-enrich", ref=f"se:{uid}", probes=tuple(matrix.probe_ids),
        bg_rate_ttest=bg_rate_ttest, bg_rate_rank=bg_rate_rank,
        group_col=group_col, level_a=level_a, level_b=level_b, alpha=alpha,
        region=(f"{spec.rep_name}", 0, n_windows),
        title=f"DMP-rate fold-enrichment {level_a} vs {level_b} across {n_windows} {spec.label} over matched bg",
    )
    return claim, n_probes


def run_te_enrichment_sweep(
    rmsk_path,
    bed_dir,
    manifest,
    contracts_dir,
    *,
    bg_rate_ttest: float,
    bg_rate_rank: float,
    group_col: str = "lineage",
    level_a: str = "Lymphoid",
    level_b: str = "Myeloid",
    alpha: float = 0.05,
    min_cov: int = 4,
    target_fdr: float = 0.05,
    panel: tuple[TeFamilySpec, ...] = PANEL,
) -> TeEnrichmentSweepResult:
    """Drive the PANEL through ONE shared e-LOND ledger as fold-enrichment-over-background claims.

    `bg_rate_ttest`/`bg_rate_rank` are the PRE-REGISTERED matched-background rates (from
    `estimate_background_dmp_rates` on random windows). Phase 1 builds every family's enrichment claim
    and registers it IN PANEL ORDER (locks alpha_t per slot); Phase 2 one `run_cycle` resolves all
    families at their locked alphas. Reports raw DMP counts too, so the honest contrast
    (real-DMPs-but-below-background) is visible."""
    contracts_dir = Path(contracts_dir)
    built: list[tuple[TeFamilySpec, object, int, int]] = []
    ledger = FDRLedger(target_fdr=target_fdr)

    fam_windows = te_family_windows_multi(
        Path(rmsk_path), [(s.key, s.rep_name, s.rep_class) for s in panel])
    matrices = extract_cpg_matrices_multi_families(
        Path(bed_dir), Path(manifest), fam_windows, min_cov=min_cov)

    for spec in panel:
        n_windows = len(fam_windows[spec.key])
        claim, n_probes = _build_family_enrichment_claim(
            spec, matrices[spec.key], n_windows, contracts_dir,
            group_col=group_col, level_a=level_a, level_b=level_b, alpha=alpha,
            bg_rate_ttest=bg_rate_ttest, bg_rate_rank=bg_rate_rank)
        ledger = register_test(ledger, claim.id, commitment_hash(claim))
        built.append((spec, claim, n_windows, n_probes))

    corpus = Corpus(claims=tuple(c for _, c, _, _ in built), fdr_ledger=ledger)
    oracles = profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public"))
    registry = enrichment_independent_registry()

    obs: dict[str, tuple[int, int, float, float]] = {}
    with using_contract_root(contracts_dir):
        clear_contract_cache()
        try:
            for _, claim, _, _ in built:
                node = claim.evaluation_plan.graph.nodes[0]
                ct = int(NDmpTTestAdapter().execute(node, (), _CTX).value)
                cr = int(NDmpRankAdapter().execute(node, (), _CTX).value)
                ft = float(EnrichmentTTestAdapter().execute(node, (), _CTX).value)
                fr = float(EnrichmentRankAdapter().execute(node, (), _CTX).value)
                obs[claim.id] = (ct, cr, ft, fr)
            result = run_cycle(
                corpus, _ENRICH_ADAPTERS, _CTX,
                adapter_registry=registry,
                oracles=oracles,
                materializations=materialization_map(corpus, _CTX),
                evidence=evidence_map(corpus),
                capability_registry=CAPABILITY_CELLS,
            )
            corpus = result.corpus
        finally:
            clear_contract_cache()

    out = TeEnrichmentSweepResult(corpus=corpus, bg_rate_ttest=bg_rate_ttest, bg_rate_rank=bg_rate_rank)
    by_id = {c.id: c for c in corpus.claims}
    ledger_by_id = {t.claim_id: t for t in corpus.fdr_ledger.tests}
    for spec, claim, n_windows, n_probes in built:
        c = by_id[claim.id]
        t = ledger_by_id.get(claim.id)
        ct, cr, ft, fr = obs.get(claim.id, (0, 0, 0.0, 0.0))
        alpha_alloc = t.alpha_allocated if t is not None else None
        out.families.append(TeEnrichmentResult(
            key=spec.key, label=spec.label, verdict=_verdict(c.status), status=c.status,
            n_windows=n_windows, n_probes=n_probes, count_ttest=ct, count_rank=cr,
            fold_ttest=ft, fold_rank=fr,
            e_value=(t.e_value if t is not None else None), alpha_allocated=alpha_alloc,
            bar=((1.0 / alpha_alloc) if alpha_alloc else None)))
    return out
