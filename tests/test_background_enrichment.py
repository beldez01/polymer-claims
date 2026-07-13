"""Background-null / fold-enrichment claim pattern (the honest recast of the TE arm).

Unlike the n-DMP count-vs-CHANCE gate, this pattern's null is a matched genomic BACKGROUND:
H0 is "the region-class per-probe lineage-DMP rate <= the matched-background rate", so a license
means the class is ENRICHED for lineage-DMPs above baseline — not merely differentially methylated
beyond noise. See docs/superpowers/notes/2026-07-11-transposable-element-methylation-strain.md.
"""
from __future__ import annotations

from polymer_grammar import Comparator, MaterializationContext
from polymer_grammar.pattern import registry

from polymer_claims.contracts import clear_contract_cache, using_contract_root
from polymer_claims.ingest.build_cpg_matrix_contract import build_cpg_matrix_contract
from polymer_claims.ingest.loyfer_wgbs import CpgMatrix

_CTX = MaterializationContext(id="M1", api_version="v1", data_version="synthetic@1")


def _matrix(n_sep: int, n_flat: int, *, n_per_group: int = 4) -> CpgMatrix:
    """A synthetic CpG matrix: `n_sep` probes separate Lymphoid~0.9/Myeloid~0.1 (each a DMP under
    both legs at 4v4), `n_flat` probes are flat ~0.5 in both lineages (never a DMP). So the observed
    per-probe DMP rate is exactly n_sep/(n_sep+n_flat) for each leg — a known fold given a background."""
    probes = [f"chr1:{1000 + 10 * i}" for i in range(n_sep + n_flat)]
    samples, meta = [], []
    for i in range(n_per_group):
        for lin in ("Lymphoid", "Myeloid"):
            s = f"{lin[:2]}{i}"
            samples.append(s)
            meta.append({"sample": s, "cell_type": f"{lin}_ct",
                         "cell_type_broad": f"{lin}_br", "lineage": lin})
    betas = []
    for p in range(n_sep + n_flat):
        row = []
        for i in range(n_per_group):
            for lin in ("Lymphoid", "Myeloid"):
                if p < n_sep:
                    row.append((0.90 if lin == "Lymphoid" else 0.10) + 0.003 * i)
                else:
                    row.append(0.50 + 0.004 * i)
        betas.append(row)
    return CpgMatrix(probe_ids=probes, samples=samples, sample_meta=meta, betas=betas)


def _contract(tmp_path, matrix, uid):
    build_cpg_matrix_contract(matrix, uid, tmp_path / "contracts", group_col="lineage")
    return tmp_path / "contracts"


def test_fold_adapters_return_family_rate_over_leg_background(tmp_path):
    from polymer_claims.background_enrichment import (
        EnrichmentRankAdapter, EnrichmentTTestAdapter, background_enrichment_claim,
    )
    m = _matrix(6, 4)                      # 6/10 probes are DMPs on each leg
    cdir = _contract(tmp_path, m, "enr_a@1")
    claim = background_enrichment_claim(
        "enr-a", ref="se:enr_a@1", probes=tuple(m.probe_ids),
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, bg_rate_ttest=0.30, bg_rate_rank=0.50,
    )
    node = claim.evaluation_plan.graph.nodes[0]
    with using_contract_root(cdir):
        clear_contract_cache()
        try:
            ft = EnrichmentTTestAdapter().execute(node, (), _CTX).value
            fr = EnrichmentRankAdapter().execute(node, (), _CTX).value
        finally:
            clear_contract_cache()
    # fold = observed DMP rate (0.6) / that-leg's matched-background rate.
    assert abs(ft - (0.6 / 0.30)) < 1e-9    # 2.0 — enriched above t-leg background
    assert abs(fr - (0.6 / 0.50)) < 1e-9    # 1.2 — enriched above rank-leg background


def test_background_enrichment_claim_criterion_is_fold_ge_one(tmp_path):
    from polymer_claims.background_enrichment import background_enrichment_claim
    m = _matrix(6, 4)
    claim = background_enrichment_claim(
        "enr-c", ref="se:enr_c@1", probes=tuple(m.probe_ids),
        group_col="lineage", level_a="Lymphoid", level_b="Myeloid",
        alpha=0.05, bg_rate_ttest=0.30, bg_rate_rank=0.50,
    )
    crit = claim.evaluation_plan.criterion
    assert crit.comparator == Comparator.GE and crit.threshold == 1.0


def test_evidence_uses_count_enrichment_evalue_with_background_p0(tmp_path):
    """The enrichment e-value is the SAME count_enrichment_evalue as the n-DMP arm, but its null is
    the matched-BACKGROUND rate (p0 = bg_rate_ttest), not chance (alpha). A family whose rate exceeds
    background yields e>1; a family below its background yields far less evidence (near/below 1)."""
    from polymer_grammar import FDRLedger
    from polymer_protocol import Corpus

    from polymer_claims.background_enrichment import background_enrichment_claim
    from polymer_claims.evidence import count_enrichment_evalue, evidence_map
    from polymer_claims.methyl_ndmp import dmp_indicators

    m = _matrix(6, 4)                      # observed DMP rate = 0.6 on the t-leg
    cdir = _contract(tmp_path, m, "enr_e@1")
    enriched = background_enrichment_claim(
        "enr-hi", ref="se:enr_e@1", probes=tuple(m.probe_ids), region=("chr1", 10, 20),
        alpha=0.05, bg_rate_ttest=0.30, bg_rate_rank=0.50)      # 0.6 > 0.30 background
    depleted = background_enrichment_claim(
        "enr-lo", ref="se:enr_e@1", probes=tuple(m.probe_ids), region=("chr1", 30, 40),
        alpha=0.05, bg_rate_ttest=0.90, bg_rate_rank=0.95)      # 0.6 < 0.90 background
    corpus = Corpus(claims=(enriched, depleted), fdr_ledger=FDRLedger(target_fdr=0.05))
    node = enriched.evaluation_plan.graph.nodes[0]
    with using_contract_root(cdir):
        clear_contract_cache()
        try:
            ev = evidence_map(corpus)
            expected = count_enrichment_evalue(dmp_indicators(node), p0=0.30)
        finally:
            clear_contract_cache()
    assert abs(ev["enr-hi"] - expected) < 1e-9
    assert ev["enr-hi"] > 1.0                    # enriched above the matched background
    assert ev["enr-lo"] < ev["enr-hi"]           # same data, higher background -> less enrichment evidence


def test_background_enrichment_pattern_is_registered():
    import polymer_claims.background_enrichment_patterns  # noqa: F401 (registers on import)

    pat = registry.get("background_enrichment", "v1")
    assert pat is not None
    # The distinguishing feature vs the n-DMP count pattern is the NULL MODEL.
    assert pat.null_model == "matched_genomic_background"
    # A between-lineage difference beyond chance is a DIFFERENT (weaker) claim — excluded here.
    assert any("chance" in x or "noise" in x for x in pat.excluded_applications)
