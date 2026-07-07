"""CES-2: region differential-methylation execution over a content-addressed SE Contract.

Two INDEPENDENT legs compute the region Δβ of the per-sample region-mean betas two genuinely
different ways — a direct group mean-difference (leg A; parametric, moment-based) vs the
Hodges–Lehmann location-shift estimator (leg B; the median of ALL pairwise differences
b_j - a_i, a robust rank-family estimator insensitive to tail/outlier behavior). The two legs
rest on different assumptions, so they can genuinely disagree on skewed betas, not just on a
coding bug — see RegionHodgesLehmannAdapter's docstring. Agreement is gated on each leg
INDEPENDENTLY satisfying the claim's criterion (CapabilityCell.agreement_mode=
"both_satisfy_criterion" in capabilities.py), not numeric closeness between the two point
estimates. Umbrella/impure (file I/O via load_contract). Grammar + protocol untouched. NOT
re-exported from __init__ (keeps base import numpy-free).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    DataHandle,
    ExecValue,
    GenomicRegion,
    OperationNode,
    PatternRef,
    PendingReason,
    SatisfactionCriterion,
    Status,
    StrengthVector,
)
from polymer_protocol import AdapterCredential, AdapterRegistry

from .adapter_identity import implementation_hash_for_adapter
from .analysis_profile import profile_oracle_id
from .contracts import load_contract, load_manifest
from .profiles import CANONICAL_EPICV2_V1

_IMPL = "methyl::region_delta_beta"


def _load_betas(
    node: OperationNode,
) -> tuple[dict[str, dict[str, float]], list[str], dict[str, str], dict[str, str]]:
    """Resolve the node's DataHandle to the per-probe-per-sample beta matrix + sample grouping + params.
    Returns (beta: dict[str, dict[str, float]], sample_ids: list[str],
    group_of: dict[str, str], params: dict[str, str]). Shared by region-Δβ and n-DMPs.
    Raises ValueError on a missing DataHandle (the evaluator degrades a raise to a node error)."""
    handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
    if handle is None:
        raise ValueError(f"{node.impl} requires a DataHandle input")
    p = {k: v for k, v in node.params}
    se = load_contract(handle.ref)
    betas_path = Path(se.access_methods[0].access_url)
    manifest = load_manifest(se)
    group_col = p["group_col"]
    sample_ids = [c["sample_id"] for c in manifest["col_data"]]
    group_of = {c["sample_id"]: c[group_col] for c in manifest["col_data"]}
    lines = betas_path.read_text().splitlines()
    header = lines[0].split("\t")[1:]
    beta: dict[str, dict[str, float]] = {}
    for ln in lines[1:]:
        cells = ln.split("\t")
        beta[cells[0]] = {sid: float(v) for sid, v in zip(header, cells[1:])}
    return beta, sample_ids, group_of, p


def _region_group_means(node: OperationNode) -> tuple[list[float], list[float]]:
    """Resolve the node's DataHandle to per-sample region-mean betas, split by the two levels.
    Returns (level_a means, level_b means). Raises on bad impl / missing probe / empty group."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    beta, sample_ids, group_of, p = _load_betas(node)
    region_probes = [s for s in p["region_probes"].split(",") if s]
    level_a, level_b = p["level_a"], p["level_b"]
    for cg in region_probes:
        if cg not in beta:
            raise KeyError(f"region probe {cg!r} not in contract")
    per_sample = {
        sid: sum(beta[cg][sid] for cg in region_probes) / len(region_probes)
        for sid in sample_ids
    }
    a = [per_sample[sid] for sid in sample_ids if group_of[sid] == level_a]
    b = [per_sample[sid] for sid in sample_ids if group_of[sid] == level_b]
    if not a or not b:
        raise ValueError(f"empty group (level_a={len(a)}, level_b={len(b)})")
    return a, b


class RegionMeanDiffAdapter:
    """Independent impl A — direct group mean-difference (level_b − level_a)."""

    identity = "methyl-meandiff-beta"

    def execute(self, node, upstream, ctx) -> ExecValue:
        a, b = _region_group_means(node)
        return ExecValue(value=(sum(b) / len(b)) - (sum(a) / len(a)))


class RegionHodgesLehmannAdapter:
    """Independent impl B — Hodges–Lehmann location-shift estimator: the median of ALL pairwise
    differences {b_j - a_i : for all i, j} over the per-sample region-mean betas. A genuinely
    different, rank-based/robust estimator from leg A's mean difference (insensitive to a skewed
    or outlier-laden tail) — unlike a leg forced to algebraically mirror leg A (the retired
    OLS-coefficient leg equalled the mean difference exactly, by construction, for any two-group
    design), this one can — and on skewed betas, does — diverge from leg A's point estimate. The
    air-gap between the two legs is gated on each leg independently clearing the claim's
    criterion (CapabilityCell.agreement_mode="both_satisfy_criterion" in capabilities.py), not
    numeric closeness or exact equality on the point estimate."""

    identity = "methyl-hodges-lehmann"

    def execute(self, node, upstream, ctx) -> ExecValue:
        a, b = _region_group_means(node)
        a_arr = np.asarray(a, dtype=float)
        b_arr = np.asarray(b, dtype=float)
        pairwise = (b_arr[:, None] - a_arr[None, :]).ravel()
        return ExecValue(value=float(np.median(pairwise)))


# Default signal region of the bundled fixture (first 5 probes, chr1:1,000,000-1,000,800).
_DEFAULT_REGION_PROBES = ("cg00000001", "cg00000002", "cg00000003", "cg00000004", "cg00000005")
_DEFAULT_REGION = ("chr1", 1_000_000, 1_000_800)


def region_delta_beta_claim(
    claim_id: str,
    *,
    ref: str = "se:epicv2_casectrl_demo@1",
    region_probes: tuple[str, ...] = _DEFAULT_REGION_PROBES,
    region: tuple[str, int, int] = _DEFAULT_REGION,
    group_col: str = "Sample_Group",
    level_a: str = "level1",
    level_b: str = "level2",
    comparator: Comparator = Comparator.GT,
    threshold: float = 0.10,
    ontology_term: str = "differential_methylation",
    strength: StrengthVector | None = None,
    with_subject: bool = True,
    oracle_ref: str | None = None,
    title: str = "region differential methylation (level2 - level1)",
) -> Claim:
    """Build a PENDING claim whose plan computes a region Δβ over the bundled SE Contract, binding
    CANONICAL_EPICV2_V1 as the apparatus (oracle_ref). `strength=None` → earned at verify. The
    `genomic_region` subject is REQUIRED for the apparatus domain ({genomic_region, cohort}); pass
    `with_subject=False` only to probe the out-of-domain precondition."""
    if oracle_ref is None:
        oracle_ref = profile_oracle_id(CANONICAL_EPICV2_V1)
    from .capabilities import REGION_DELTA_BETA_CELL
    from polymer_grammar.capability import build_evaluation_plan

    plan = build_evaluation_plan(
        REGION_DELTA_BETA_CELL,
        params={"region_probes": ",".join(region_probes), "group_col": group_col,
                "level_a": level_a, "level_b": level_b},
        data_ref=ref, criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
        oracle_ref=oracle_ref)
    subject = None
    if with_subject:
        chrom, start, end = region
        subject = GenomicRegion(
            id=f"{chrom}:{start}-{end}",
            display=f"{chrom}:{start:,}-{end:,}",
            assembly="hg38",
            chrom=chrom,
            start=start,
            end=end,
        )
    return Claim(
        id=claim_id,
        title=title,
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term=ontology_term),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        strength=strength,
        subject=subject,
        evaluation_plan=plan,
    )


def methyl_independent_registry() -> AdapterRegistry:
    """Credentials asserting the two legs are genuinely independent (distinct owners + impl hashes),
    so the #5 gate licenses on their agreement."""
    return AdapterRegistry(credentials=(
        AdapterCredential(
            identity="methyl-meandiff-beta",
            owner="owner-meandiff",
            implementation_hash=implementation_hash_for_adapter(RegionMeanDiffAdapter),
        ),
        AdapterCredential(
            identity="methyl-hodges-lehmann",
            owner="owner-hl",
            implementation_hash=implementation_hash_for_adapter(RegionHodgesLehmannAdapter),
        ),
    ))
