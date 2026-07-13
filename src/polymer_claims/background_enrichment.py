"""Background-null / fold-enrichment adapters + claim builder (the honest TE recast).

Two INDEPENDENT legs reuse the n-DMP per-probe DMP call (methyl_ndmp) — pooled-t (leg A) and
Mann-Whitney rank-sum (leg B) — but each returns a FOLD: the observed per-probe lineage-DMP rate
divided by that leg's PRE-REGISTERED matched-genomic-background DMP rate (a node param, computed from
random windows blind to the family). The claim licenses iff BOTH legs clear fold >= 1
(`both_satisfy_criterion`) AND the count-enrichment e-value — the SAME `count_enrichment_evalue` as the
n-DMP arm, but with `p0 = background_rate` instead of `p0 = alpha` — clears the e-LOND bar. So the null
is a matched BACKGROUND, not chance: a license means ENRICHED above baseline, the claim the n-DMP gate
cannot make. Umbrella/impure (reads the contract via methyl_ndmp's loaders). The e-value's leg-A view
(dmp_indicators) and p0 (bg_rate_ttest) live in evidence.py — kept consistent with leg A here.
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ExecValue,
    GenomicRegion,
    PatternRef,
    PendingReason,
    SatisfactionCriterion,
    Status,
    StrengthVector,
)
from polymer_protocol import AdapterCredential, AdapterRegistry

from .adapter_identity import implementation_hash_for_adapter
from .analysis_profile import profile_oracle_id
from .methyl_ndmp import _alpha, _n_dmps, _per_probe_pvalues, _per_probe_pvalues_rank, _pooled_t
from .profiles import CANONICAL_EPICV2_V1

_ENRICH_IMPL = "methyl::enrichment"


def _bg_rate(node, key: str) -> float:
    """The pre-registered matched-background DMP rate for one leg, from the node params (in (0,1))."""
    return float(dict(node.params)[key])


def _fold(node, pvalues: dict, *, bg_key: str) -> float:
    """observed per-probe DMP rate (count/N) / that-leg's matched-background rate. Empty -> 0.0."""
    n = len(pvalues)
    if n == 0:
        return 0.0
    expected = _bg_rate(node, bg_key) * n
    return (_n_dmps(pvalues, _alpha(node)) / expected) if expected > 0 else 0.0


class EnrichmentTTestAdapter:
    """Leg A — fold of the pooled-t DMP rate over the matched-background t-leg rate (bg_rate_ttest)."""

    identity = "methyl-enrichment-ttest"

    def execute(self, node, upstream, ctx) -> ExecValue:
        return ExecValue(value=float(_fold(node, _per_probe_pvalues(node, leg=_pooled_t),
                                           bg_key="bg_rate_ttest")))


class EnrichmentRankAdapter:
    """Leg B — fold of the rank-sum DMP rate over the matched-background rank-leg rate (bg_rate_rank).
    A genuinely different statistical procedure from leg A (rank-based; no normality/equal-variance),
    so it can disagree with leg A on a shared-assumption failure — the air-gap is each leg
    independently clearing fold >= 1 (both_satisfy_criterion), not numeric closeness on the fold."""

    identity = "methyl-enrichment-rank"

    def execute(self, node, upstream, ctx) -> ExecValue:
        return ExecValue(value=float(_fold(node, _per_probe_pvalues_rank(node),
                                           bg_key="bg_rate_rank")))


def background_enrichment_claim(
    claim_id: str,
    *,
    ref: str,
    probes: tuple[str, ...],
    bg_rate_ttest: float,
    bg_rate_rank: float,
    group_col: str = "lineage",
    level_a: str = "Lymphoid",
    level_b: str = "Myeloid",
    alpha: float = 0.05,
    region: tuple[str, int, int] | None = None,
    oracle_ref: str | None = None,
    strength: StrengthVector | None = None,
    title: str = "region-class DMP-rate fold-enrichment over matched background",
) -> Claim:
    """Build a PENDING enrichment claim: licenses iff the family's per-probe lineage-DMP rate clears
    its matched-background rate on BOTH legs (fold >= 1) AND the count e-value (p0=bg_rate) clears the
    e-LOND bar. Mirrors n_dmps_claim, but the criterion is fold>=1 and the null is the background,
    carried by the bg_rate_ttest/bg_rate_rank params. `strength=None` -> earned at verify."""
    if oracle_ref is None:
        oracle_ref = profile_oracle_id(CANONICAL_EPICV2_V1)
    from polymer_grammar.capability import build_evaluation_plan

    from .capabilities import BACKGROUND_ENRICHMENT_CELL

    plan = build_evaluation_plan(
        BACKGROUND_ENRICHMENT_CELL,
        params={"probes": ",".join(probes), "group_col": group_col,
                "level_a": level_a, "level_b": level_b, "alpha": str(alpha),
                "bg_rate_ttest": str(bg_rate_ttest), "bg_rate_rank": str(bg_rate_rank)},
        data_ref=ref,
        criterion=SatisfactionCriterion(comparator=Comparator.GE, threshold=1.0),
        oracle_ref=oracle_ref,
    )
    chrom, start, end = region or ("chr1", 1_000_000, 1_004_800)
    subject = GenomicRegion(
        id=f"{chrom}:{start}-{end}", display=f"{chrom}:{start:,}-{end:,}",
        assembly="hg38", chrom=chrom, start=start, end=end,
    )
    return Claim(
        id=claim_id,
        title=title,
        pattern=PatternRef(id="background_enrichment", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="differential_methylation"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        strength=strength,
        subject=subject,
        evaluation_plan=plan,
    )


def enrichment_independent_registry() -> AdapterRegistry:
    """Credentials asserting the two enrichment legs are genuinely independent (distinct owners+hashes)."""
    return AdapterRegistry(credentials=(
        AdapterCredential(
            identity="methyl-enrichment-ttest",
            owner="owner-enrich-ttest",
            implementation_hash=implementation_hash_for_adapter(EnrichmentTTestAdapter),
        ),
        AdapterCredential(
            identity="methyl-enrichment-rank",
            owner="owner-enrich-rank",
            implementation_hash=implementation_hash_for_adapter(EnrichmentRankAdapter),
        ),
    ))
