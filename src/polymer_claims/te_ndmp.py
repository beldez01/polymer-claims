"""Transposable-element n-DMP FAMILY SWEEP over the real Loyfer 2023 WGBS atlas.

Generalizes the single HERV-K drive (`rip_hervk_ndmp`) into a PRE-REGISTERED PANEL of TE subfamilies,
each asking the same severe test: "across all elements of family F, do >= k CpG probes come out
differentially methylated between two cell lineages (level_a vs level_b), under BOTH a pooled-t and a
rank-sum leg?" One count-enrichment e-value per family is charged to ONE shared e-LOND ledger, so the
whole sweep is a single online-FDR-controlled experiment — not N independent slot-1 gates.

Pre-registration integrity (commit-before-data):
  * PANEL and its ORDER are fixed in source (this file, committed) BEFORE any atlas byte is read.
    Registration order sets each slot's locked alpha_t = target_fdr * gamma_t * (D_{t-1}+1); a wrong
    order cannot be chosen post hoc to license a family.
  * Each family's count floor k is `preregistered_k(n_probes, alpha)` = ceil(3*alpha*N) — a function of
    the probe COUNT and alpha only, never of the observed betas.
  * `register_test` locks alpha_t before execution; `run_cycle`/verify resolves each family at its
    LOCKED alpha (match-gate), so the bar a family faces is frozen at registration.

Runtime note: `extract_cpg_matrix_multi` scans each of the ~47 sample BEDs once PER family, so a
6-family sweep is ~6 passes over the atlas (minutes each). AluY (~105k elements) is EXCLUDED from the
panel by an explicit tractability rule (see `EXCLUDED`), logged — never silently dropped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from polymer_grammar import Comparator, FDRLedger, MaterializationContext, Status, register_test
from polymer_grammar.commitment import commitment_hash
from polymer_protocol import Corpus, run_cycle

from .analysis_profile import profile_oracle_registry
from .capabilities import CAPABILITY_CELLS
from .contracts import clear_contract_cache, using_contract_root
from .evidence import evidence_map
from .ingest.build_cpg_matrix_contract import build_cpg_matrix_contract
from .ingest.loyfer_wgbs import extract_cpg_matrices_multi_families
from .ingest.te_loci import te_family_windows_multi
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


@dataclass(frozen=True)
class TeFamilySpec:
    """One pre-registered TE subfamily. `rep_name`/`rep_class` are the exact rmsk.txt strings
    (verified against ~/Desktop/PolymerGenomicsAPI/data/repeatmasker/rmsk.txt)."""

    key: str            # short claim-id stem, e.g. "l1hs"
    rep_name: str       # rmsk repName, e.g. "L1HS"
    rep_class: str      # rmsk repClass, e.g. "LINE"
    label: str          # human title fragment
    note: str           # biological rationale (why this family is in the panel)


# --- THE PRE-REGISTERED PANEL (fixed order = fixed e-LOND slot allocation) ---
# Order = descending prior plausibility of lineage-differential methylation. HERV-K first: it is the
# positive control already LICENSED in the immuno arm, so a lineage-DMP signal there is the sanity
# anchor. Fixed BEFORE reading the atlas; do not reorder to chase a license.
PANEL: tuple[TeFamilySpec, ...] = (
    TeFamilySpec("hervk_ltr5", "LTR5_Hs", "LTR",
                 "HERV-K(HML-2) LTR5_Hs promoter LTRs",
                 "positive control: youngest, most intact ERVK promoter LTR; licensed in immuno arm"),
    TeFamilySpec("l1hs", "L1HS", "LINE",
                 "L1HS (LINE-1 Homo sapiens-specific) elements",
                 "only autonomously active human retrotransposon; L1 methylation is lineage/cancer-labile"),
    TeFamilySpec("hervh_ltr7", "LTR7", "LTR",
                 "HERV-H LTR7 5' LTRs",
                 "HERV-H LTR7 drives pluripotency-associated transcription; regulatory, lineage-patterned"),
    TeFamilySpec("hervw_ltr17", "LTR17", "LTR",
                 "HERV-W LTR17 LTRs",
                 "ERV1/HERV-W lineage (syncytin-1); placenta/immune-relevant regulatory LTRs"),
    TeFamilySpec("sva_d", "SVA_D", "Retroposon",
                 "SVA_D composite retroelements",
                 "youngest large hominid-specific composite element; CpG-rich, methylation-sensitive"),
    TeFamilySpec("aluya5", "AluYa5", "SINE",
                 "AluYa5 (youngest active Alu subfamily)",
                 "most abundant TE class; AluYa5 is a young, still-mobilizing SINE subfamily"),
)

# Explicitly excluded (logged, not silently dropped): AluY sensu lato is ~105k elements on the standard
# chromosomes; gathering CpGs across that many windows x47 samples is not tractable for this sweep.
# AluYa5 (a young Alu subfamily, ~3.9k elements) stands in for the SINE class.
EXCLUDED: tuple[tuple[str, str], ...] = (
    ("AluY", "~105k elements — over the per-family tractability budget; AluYa5 represents SINEs"),
)


@dataclass
class TeFamilyResult:
    key: str
    label: str
    verdict: str            # "LICENSED" | "REJECTED" | "PENDING"
    status: Status
    n_windows: int          # elements gathered from rmsk
    n_probes: int           # complete-case CpG probes across all windows
    k: int                  # pre-registered count floor
    count_ttest: int        # leg A observed DMP count (pooled-t)
    count_rank: int         # leg B observed DMP count (rank-sum)
    e_value: float | None   # count-enrichment e-value at this family's pre-registered slot
    alpha_allocated: float | None  # LOCKED e-LOND level for this slot
    bar: float | None       # 1 / alpha_allocated (the e-value must clear this)


@dataclass
class TeSweepResult:
    families: list[TeFamilyResult] = field(default_factory=list)
    corpus: object = None
    excluded: tuple[tuple[str, str], ...] = EXCLUDED


def _verdict(status) -> str:
    if status == Status.LICENSED:
        return "LICENSED"
    if status == Status.REJECTED:
        return "REJECTED"
    return "PENDING"


def _build_family_claim(spec: TeFamilySpec, matrix, n_windows, contracts_dir,
                        *, group_col, level_a, level_b, alpha):
    """From this family's already-extracted complete-case CpG matrix -> SE-Contract -> a PENDING n-DMP
    claim whose count floor k is set from N and alpha ONLY. Returns (claim, n_probes, k)."""
    n_probes = len(matrix.probe_ids)
    k = preregistered_k(n_probes, alpha)  # set BEFORE any count is observed
    uid = f"te_{spec.key}_ndmp_{level_a}_{level_b}@1".lower()
    build_cpg_matrix_contract(matrix, uid, contracts_dir, group_col=group_col)
    claim = n_dmps_claim(
        f"te-{spec.key}-ndmp",
        ref=f"se:{uid}",
        probes=tuple(matrix.probe_ids),
        region=(f"{spec.rep_name}", 0, n_windows),
        group_col=group_col, level_a=level_a, level_b=level_b,
        alpha=alpha, k=float(k), comparator=Comparator.GE,
        title=f"n-DMPs {level_a} vs {level_b} across {n_windows} {spec.label}",
    )
    return claim, n_probes, k


def run_te_family_sweep(
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
    target_fdr: float = 0.05,
    panel: tuple[TeFamilySpec, ...] = PANEL,
) -> TeSweepResult:
    """Drive the whole PANEL through ONE shared e-LOND ledger.

    Phase 1 (commit-before-data): build every family's claim (windows + contract + data-blind k) and
    register each into the shared ledger IN PANEL ORDER — this locks alpha_t per slot. Phase 2: one
    `run_cycle` resolves all families at their locked alphas (match-gate). Returns per-family verdicts.
    """
    contracts_dir = Path(contracts_dir)
    built: list[tuple[TeFamilySpec, object, int, int, int]] = []
    ledger = FDRLedger(target_fdr=target_fdr)

    # Phase 0 — ONE rmsk parse + ONE atlas pass for the whole panel (families share the BED scan).
    fam_windows = te_family_windows_multi(
        Path(rmsk_path), [(s.key, s.rep_name, s.rep_class) for s in panel]
    )
    matrices = extract_cpg_matrices_multi_families(
        Path(bed_dir), Path(manifest), fam_windows, min_cov=min_cov
    )

    # Phase 1 — build + PRE-REGISTER in panel order (alpha_t locked here, before execution).
    for spec in panel:
        n_windows = len(fam_windows[spec.key])
        claim, n_probes, k = _build_family_claim(
            spec, matrices[spec.key], n_windows, contracts_dir,
            group_col=group_col, level_a=level_a, level_b=level_b, alpha=alpha,
        )
        ledger = register_test(ledger, claim.id, commitment_hash(claim))
        built.append((spec, claim, n_windows, n_probes, k))

    corpus = Corpus(claims=tuple(c for _, c, _, _, _ in built), fdr_ledger=ledger)
    oracles = profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public"))
    registry = ndmp_independent_registry()

    # Observe the two legs directly for reporting (does NOT affect the gate; the gate is run_cycle).
    counts: dict[str, tuple[int, int]] = {}
    with using_contract_root(contracts_dir):
        clear_contract_cache()
        try:
            for _, claim, _, _, _ in built:
                node = claim.evaluation_plan.graph.nodes[0]
                ct = int(NDmpTTestAdapter().execute(node, (), _CTX).value)
                cr = int(NDmpRankAdapter().execute(node, (), _CTX).value)
                counts[claim.id] = (ct, cr)
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

    out = TeSweepResult(corpus=corpus)
    by_id = {c.id: c for c in corpus.claims}
    ledger_by_id = {t.claim_id: t for t in corpus.fdr_ledger.tests}
    for spec, claim, n_windows, n_probes, k in built:
        c = by_id[claim.id]
        t = ledger_by_id.get(claim.id)
        ct, cr = counts.get(claim.id, (0, 0))
        e_value = t.e_value if t is not None else None
        alpha_alloc = t.alpha_allocated if t is not None else None
        bar = (1.0 / alpha_alloc) if (alpha_alloc) else None
        out.families.append(TeFamilyResult(
            key=spec.key, label=spec.label, verdict=_verdict(c.status), status=c.status,
            n_windows=n_windows, n_probes=n_probes, k=k, count_ttest=ct, count_rank=cr,
            e_value=e_value, alpha_allocated=alpha_alloc, bar=bar,
        ))
    return out
