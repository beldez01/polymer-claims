"""TE multi-contrast CAMPAIGN — a large pre-registered claim push over the Loyfer 2023 WGBS atlas.

Extracts the 6-family TE window matrices AND the matched-background random-window matrices ONCE (all 47
samples; every grouping column — lineage/cell_type_broad/cell_type — is written into each contract, so one
extraction serves every contrast), then runs a PRE-REGISTERED panel of lineage / cell-type contrasts. For
each contrast it runs BOTH gates through their own shared e-LOND ledgers:
  * the n-DMP beyond-chance gate (`te_ndmp`) — "more lineage-DMPs than chance",
  * the background-enrichment gate (`te_enrichment`/`background_enrichment`) — "enriched over a matched
    genomic background".
So one atlas extraction yields up to N_contrasts x 2 x 6 pre-registered claims, each contrast an
INDEPENDENT online-FDR-controlled experiment. Not fishing: the CONTRAST panel, the FAMILY panel, and the
family ORDER are all fixed in source before any atlas byte is read, and each contrast's e-LOND bars are
locked at registration.
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
from .ingest.te_loci import random_background_windows, te_family_windows_multi
from .materialization import materialization_map
from .methyl_ndmp import NDmpRankAdapter, NDmpTTestAdapter, n_dmps_claim, ndmp_independent_registry
from .profiles import CANONICAL_EPICV2_V1
from .rip_mhc_ndmp import preregistered_k
from .te_ndmp import PANEL, TeFamilySpec

_CTX = MaterializationContext(id="M1", api_version="v1", data_version="loyfer_2023@1")
_NDMP_ADAPTERS = (NDmpTTestAdapter(), NDmpRankAdapter())
_ENR_ADAPTERS = (EnrichmentTTestAdapter(), EnrichmentRankAdapter())


@dataclass(frozen=True)
class Contrast:
    """One pre-registered two-group contrast over a manifest column (>=2 samples per level needed)."""

    key: str
    group_col: str
    level_a: str
    level_b: str
    note: str


# THE PRE-REGISTERED CONTRAST PANEL — immune-ontology-principled pairwise contrasts, fixed BEFORE any
# atlas byte is read. Lymphoid-vs-Myeloid is the baseline (already reported); the rest partition the
# hematopoietic tree along established axes (lymphoid subsets, T differentiation, myeloid maturation,
# erythroid-vs-myeloid, cross-lineage cell types). Order is fixed; do not reorder to chase a license.
CONTRASTS: tuple[Contrast, ...] = (
    Contrast("lymphoid_vs_myeloid", "lineage", "Lymphoid", "Myeloid", "primary lineage split (baseline)"),
    Contrast("tcell_vs_bcell", "cell_type_broad", "T_cell", "B_cell", "lymphoid: T vs B"),
    Contrast("tcell_vs_nk", "cell_type_broad", "T_cell", "NK", "lymphoid: T vs NK"),
    Contrast("bcell_vs_nk", "cell_type_broad", "B_cell", "NK", "lymphoid: B vs NK"),
    Contrast("tmemory_vs_tnaive", "cell_type_broad", "T_memory", "T_naive", "T differentiation: memory vs naive"),
    Contrast("macrophage_vs_monocyte", "cell_type_broad", "Macrophage", "Monocyte", "myeloid maturation"),
    Contrast("monocyte_vs_granulocyte", "cell_type_broad", "Monocyte", "Granulocyte", "myeloid subsets"),
    Contrast("macrophage_vs_granulocyte", "cell_type_broad", "Macrophage", "Granulocyte", "myeloid: mac vs gran"),
    Contrast("erythroid_vs_granulocyte", "cell_type_broad", "Erythroid", "Granulocyte", "erythroid vs myeloid"),
    Contrast("erythroid_vs_monocyte", "cell_type_broad", "Erythroid", "Monocyte", "erythroid vs monocyte"),
    Contrast("nk_vs_monocyte", "cell_type_broad", "NK", "Monocyte", "lymphoid vs myeloid cell type"),
    Contrast("tcell_vs_monocyte", "cell_type_broad", "T_cell", "Monocyte", "T vs monocyte"),
)


@dataclass
class FamilyVerdict:
    key: str
    label: str
    verdict: str
    status: object
    n_probes: int
    count_ttest: int
    count_rank: int
    e_value: float | None
    bar: float | None
    fold_ttest: float | None = None
    fold_rank: float | None = None


@dataclass
class ContrastResult:
    contrast: Contrast
    n_a: int
    n_b: int
    bg_rate_ttest: float
    bg_rate_rank: float
    ndmp: list[FamilyVerdict] = field(default_factory=list)
    enrichment: list[FamilyVerdict] = field(default_factory=list)
    ndmp_corpus: object = None
    enrichment_corpus: object = None
    skipped: str | None = None


@dataclass
class CampaignResult:
    contrasts: list[ContrastResult] = field(default_factory=list)


def _verdict(status) -> str:
    if status == Status.LICENSED:
        return "LICENSED"
    if status == Status.REJECTED:
        return "REJECTED"
    return "PENDING"


def _level_counts(manifest_path: Path, group_col: str) -> dict[str, int]:
    """Sample counts per level of `group_col` from the manifest (for the >=2/level guard)."""
    import collections
    rows = [ln.split("\t") for ln in Path(manifest_path).read_text().splitlines() if ln.strip()]
    hdr = rows[0]
    if group_col not in hdr:
        return {}
    gi = hdr.index(group_col)
    return dict(collections.Counter(r[gi] for r in rows[1:]))


def _run_panel(panel, matrices, fam_uid, *, make_claim, adapters, registry, target_fdr, observe_fold):
    """Register + resolve one family panel through a fresh e-LOND ledger. Assumes the family contracts
    already exist under the active contract root. `make_claim(spec, ref, m) -> claim`; `observe_fold` is
    None (n-DMP) or a fn(node) -> (fold_t, fold_r). Returns (list[FamilyVerdict], corpus)."""
    ledger = FDRLedger(target_fdr=target_fdr)
    built = []
    for spec in panel:
        m = matrices[spec.key]
        claim = make_claim(spec, f"se:{fam_uid(spec.key)}", m)
        ledger = register_test(ledger, claim.id, commitment_hash(claim))
        built.append((spec, claim, len(m.probe_ids)))
    corpus = Corpus(claims=tuple(c for _, c, _ in built), fdr_ledger=ledger)
    oracles = profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public"))

    obs = {}
    for spec, claim, _ in built:
        node = claim.evaluation_plan.graph.nodes[0]
        ct = int(NDmpTTestAdapter().execute(node, (), _CTX).value)
        cr = int(NDmpRankAdapter().execute(node, (), _CTX).value)
        fold = observe_fold(node) if observe_fold else (None, None)
        obs[claim.id] = (ct, cr, fold[0], fold[1])
    result = run_cycle(
        corpus, adapters, _CTX, adapter_registry=registry, oracles=oracles,
        materializations=materialization_map(corpus, _CTX),
        evidence=evidence_map(corpus), capability_registry=CAPABILITY_CELLS)
    corpus = result.corpus

    by_id = {c.id: c for c in corpus.claims}
    led = {t.claim_id: t for t in corpus.fdr_ledger.tests}
    verdicts = []
    for spec, claim, n_probes in built:
        c = by_id[claim.id]
        t = led.get(claim.id)
        ct, cr, ft, fr = obs[claim.id]
        alpha_alloc = t.alpha_allocated if t else None
        verdicts.append(FamilyVerdict(
            key=spec.key, label=spec.label, verdict=_verdict(c.status), status=c.status,
            n_probes=n_probes, count_ttest=ct, count_rank=cr,
            e_value=(t.e_value if t else None),
            bar=((1.0 / alpha_alloc) if alpha_alloc else None), fold_ttest=ft, fold_rank=fr))
    return verdicts, corpus


def _bg_rates(bg_matrices, bg_uid, con: Contrast, alpha: float) -> tuple[float, float]:
    """Matched-background per-probe DMP rate for THIS contrast, pooled over the random-window contracts."""
    tot_n = tot_t = tot_r = 0
    for key, m in bg_matrices.items():
        n = len(m.probe_ids)
        if not n:
            continue
        claim = n_dmps_claim(
            f"bg-{con.key}-{key}", ref=f"se:{bg_uid(key)}", probes=tuple(m.probe_ids),
            group_col=con.group_col, level_a=con.level_a, level_b=con.level_b,
            alpha=alpha, k=1.0, comparator=Comparator.GE)
        node = claim.evaluation_plan.graph.nodes[0]
        tot_t += int(NDmpTTestAdapter().execute(node, (), _CTX).value)
        tot_r += int(NDmpRankAdapter().execute(node, (), _CTX).value)
        tot_n += n
    if tot_n == 0:
        raise ValueError("no complete-case background probes")
    return tot_t / tot_n, tot_r / tot_n


def run_te_campaign(
    rmsk_path,
    bed_dir,
    manifest,
    contracts_dir,
    *,
    contrasts: tuple[Contrast, ...] = CONTRASTS,
    panel: tuple[TeFamilySpec, ...] = PANEL,
    bg_reps: int = 5,
    bg_windows: int = 6000,
    bg_window_size: int = 1500,
    alpha: float = 0.05,
    min_cov: int = 4,
    target_fdr: float = 0.05,
    on_contrast=None,
) -> CampaignResult:
    """Extract ONCE, then run every contrast x {n-DMP, enrichment}. `on_contrast(cr)` is called after each
    contrast (for incremental logging/bundling). Returns the whole CampaignResult."""
    contracts_dir = Path(contracts_dir)
    manifest = Path(manifest)

    # Phase 0 — ONE rmsk parse + ONE atlas pass for families AND background; build all contracts ONCE.
    fam_windows = te_family_windows_multi(
        Path(rmsk_path), [(s.key, s.rep_name, s.rep_class) for s in panel])
    fam_matrices = extract_cpg_matrices_multi_families(
        Path(bed_dir), manifest, fam_windows, min_cov=min_cov)
    bg_by_rep = {f"bg{i}": random_background_windows(bg_windows, bg_window_size, seed=1000 + i)
                 for i in range(bg_reps)}
    bg_matrices = extract_cpg_matrices_multi_families(Path(bed_dir), manifest, bg_by_rep, min_cov=min_cov)

    def fam_uid(k):
        return f"te_camp_{k}@1".lower()

    def bg_uid(k):
        return f"te_camp_bg_{k}@1".lower()

    for spec in panel:
        build_cpg_matrix_contract(fam_matrices[spec.key], fam_uid(spec.key), contracts_dir,
                                  group_col="lineage")
    for key, m in bg_matrices.items():
        if m.probe_ids:
            build_cpg_matrix_contract(m, bg_uid(key), contracts_dir, group_col="lineage")

    counts = {gc: _level_counts(manifest, gc)
              for gc in {c.group_col for c in contrasts}}
    out = CampaignResult()

    # Phase 1 — one warm contract cache for the whole loop (contract content is contrast-invariant).
    with using_contract_root(contracts_dir):
        clear_contract_cache()
        try:
            for con in contrasts:
                lc = counts.get(con.group_col, {})
                n_a, n_b = lc.get(con.level_a, 0), lc.get(con.level_b, 0)
                cr = ContrastResult(contrast=con, n_a=n_a, n_b=n_b, bg_rate_ttest=0.0, bg_rate_rank=0.0)
                if n_a < 2 or n_b < 2:
                    cr.skipped = f"insufficient samples ({con.level_a}={n_a}, {con.level_b}={n_b})"
                    out.contrasts.append(cr)
                    if on_contrast:
                        on_contrast(cr)
                    continue

                def make_ndmp(spec, ref, m, _con=con):
                    k = preregistered_k(len(m.probe_ids), alpha)
                    return n_dmps_claim(
                        f"te-{_con.key}-{spec.key}-ndmp", ref=ref, probes=tuple(m.probe_ids),
                        region=(spec.rep_name, 0, len(fam_windows[spec.key])),
                        group_col=_con.group_col, level_a=_con.level_a, level_b=_con.level_b,
                        alpha=alpha, k=float(k), comparator=Comparator.GE,
                        title=f"n-DMPs {_con.level_a} vs {_con.level_b} across {spec.label}")

                bg_t, bg_r = _bg_rates(bg_matrices, bg_uid, con, alpha)
                cr.bg_rate_ttest, cr.bg_rate_rank = bg_t, bg_r

                def make_enrich(spec, ref, m, _con=con, _bt=bg_t, _br=bg_r):
                    return background_enrichment_claim(
                        f"te-{_con.key}-{spec.key}-enrich", ref=ref, probes=tuple(m.probe_ids),
                        bg_rate_ttest=_bt, bg_rate_rank=_br,
                        region=(spec.rep_name, 0, len(fam_windows[spec.key])),
                        group_col=_con.group_col, level_a=_con.level_a, level_b=_con.level_b, alpha=alpha,
                        title=f"DMP-rate fold-enrichment {_con.level_a} vs {_con.level_b} across {spec.label}")

                def fold(node):
                    return (float(EnrichmentTTestAdapter().execute(node, (), _CTX).value),
                            float(EnrichmentRankAdapter().execute(node, (), _CTX).value))

                # Per-contrast resilience: an unattended overnight run must not die on one bad contrast
                # (e.g. a degenerate sample subset). Record the error on the ContrastResult and continue.
                try:
                    cr.ndmp, cr.ndmp_corpus = _run_panel(
                        panel, fam_matrices, fam_uid, make_claim=make_ndmp, adapters=_NDMP_ADAPTERS,
                        registry=ndmp_independent_registry(), target_fdr=target_fdr, observe_fold=None)
                    cr.enrichment, cr.enrichment_corpus = _run_panel(
                        panel, fam_matrices, fam_uid, make_claim=make_enrich, adapters=_ENR_ADAPTERS,
                        registry=enrichment_independent_registry(), target_fdr=target_fdr,
                        observe_fold=fold)
                except Exception as e:  # noqa: BLE001 — resilience is the point; the error is recorded
                    cr.skipped = f"error: {type(e).__name__}: {e}"
                out.contrasts.append(cr)
                if on_contrast:
                    on_contrast(cr)
        finally:
            clear_contract_cache()
    return out
