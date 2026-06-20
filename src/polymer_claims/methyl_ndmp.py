"""n-DMPs-at-FDR: the count of differentially-methylated probes (a probe is a DMP iff its per-probe
two-group pooled t-test p-value < alpha), as a second scalar reduction alongside region-Δβ. Two
independent legs compute the per-probe t two ways (manual pooled-t vs OLS-coef t) and AGREE on the
integer count -> air-gap. Umbrella/impure (reads the contract via _load_betas). NOT re-exported from
__init__ (base import stays numpy-free). The count's e-value (count_enrichment_evalue) lives in
evidence.py. See docs/superpowers/specs/2026-06-14-n-dmps-at-fdr-design.md.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    ComputeGraph,
    DataHandle,
    EvaluationPlan,
    ExecValue,
    GenomicRegion,
    MeasurementBasis,
    OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec,
    SatisfactionCriterion,
    Status,
    StrengthVector,
)
from polymer_protocol import AdapterCredential, AdapterRegistry

from .adapter_identity import implementation_hash_for_adapter
from .analysis_profile import profile_oracle_id
from .contracts import load_contract
from .methyl_adapters import _load_betas
from .profiles import CANONICAL_EPICV2_V1

_NDMP_IMPL = "methyl::n_dmps"


# --- Student-t two-sided p-value via the regularized incomplete beta (pure-Python, no scipy) ---

# Lentz modified continued-fraction; Press et al., "Numerical Recipes" §6.4 (betacf).
def _betacf(a: float, b: float, x: float) -> float:
    """Lentz continued-fraction expansion for the regularized incomplete beta."""
    # MAXIT=300 / EPS=3e-16 / FPMIN=1e-300: standard convergence / machine-eps / underflow guards.
    MAXIT, EPS, FPMIN = 300, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _t_two_sided_p(t: float, df: int) -> float:
    """Two-sided Student-t p-value = I_{df/(df+t^2)}(df/2, 1/2). t=0 -> 1.0; |t|->inf -> 0.0."""
    if df <= 0:
        raise ValueError("df must be positive")
    x = df / (df + t * t)
    return _betai(df / 2.0, 0.5, x)


# --- per-probe two-group test ---

def _split(beta_row: dict[str, float], sample_ids, group_of, level_a, level_b):
    a = np.array([beta_row[s] for s in sample_ids if group_of[s] == level_a], dtype=float)
    b = np.array([beta_row[s] for s in sample_ids if group_of[s] == level_b], dtype=float)
    if len(a) < 2 or len(b) < 2:
        raise ValueError("need >=2 samples per group for a t-test")
    return a, b


def _pooled_t(a: np.ndarray, b: np.ndarray) -> tuple[float, int]:
    """Manual pooled (equal-variance) two-sample t-statistic + df. Leg A."""
    na, nb = len(a), len(b)
    df = na + nb - 2
    sp2 = ((a.var(ddof=1) * (na - 1)) + (b.var(ddof=1) * (nb - 1))) / df
    se = math.sqrt(sp2 * (1.0 / na + 1.0 / nb))
    if se == 0.0:
        # se==0: identical values -> t=0 -> p=1.0 (not a DMP); distinct constants -> inf t -> p=0.0 (always a DMP).
        return (0.0 if a.mean() == b.mean() else math.inf, df)
    return (float(b.mean() - a.mean()) / se, df)


def _per_probe_pvalues(node: OperationNode, *, leg) -> dict[str, float]:
    """Per-probe two-sided p-values over the node's `probes` param, using the `leg` t-statistic fn.

    leg: Callable[[np.ndarray, np.ndarray], tuple[float, int]] returning (t_statistic, degrees_of_freedom).
    """
    beta, sample_ids, group_of, p = _load_betas(node)
    probes = [s for s in p["probes"].split(",") if s]
    level_a, level_b = p["level_a"], p["level_b"]
    out: dict[str, float] = {}
    for cg in probes:
        if cg not in beta:
            raise KeyError(f"probe {cg!r} not in contract")
        a, b = _split(beta[cg], sample_ids, group_of, level_a, level_b)
        t, df = leg(a, b)
        out[cg] = 0.0 if math.isinf(t) else _t_two_sided_p(t, df)
    return out


def _n_dmps(pvalues: dict[str, float], alpha: float) -> int:
    return sum(1 for v in pvalues.values() if v < alpha)


def dmp_indicators(node: OperationNode) -> list[int]:
    """Per-probe DMP indicators (1 iff p < alpha) using the pooled-t leg — the e-value's view."""
    alpha = float(dict(node.params)["alpha"])
    pvals = _per_probe_pvalues(node, leg=_pooled_t)
    return [1 if v < alpha else 0 for v in pvals.values()]


def _alpha(node) -> float:
    return float(dict(node.params)["alpha"])


def _ols_t(a: np.ndarray, b: np.ndarray) -> tuple[float, int]:
    """OLS group-coefficient t-statistic + df (numpy lstsq). Leg B — equals _pooled_t for two groups."""
    na, nb = len(a), len(b)
    df = na + nb - 2
    y = np.concatenate([a, b])
    ind = np.concatenate([np.zeros(na), np.ones(nb)])
    X = np.column_stack([np.ones_like(ind), ind])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    mse = float(resid @ resid) / df
    xtx_inv = np.linalg.inv(X.T @ X)
    se = math.sqrt(mse * float(xtx_inv[1, 1]))
    # coef[1] == mean(b) - mean(a) for two-group OLS, so this mirrors _pooled_t's degenerate guard
    if se == 0.0:
        return (0.0 if coef[1] == 0.0 else math.inf), df
    return (float(coef[1]) / se, df)


class NDmpTTestAdapter:
    """Independent leg A — DMP count via the manual pooled two-sample t-test."""

    identity = "methyl-ndmp-ttest"

    def execute(self, node, upstream, ctx) -> ExecValue:
        return ExecValue(value=float(_n_dmps(_per_probe_pvalues(node, leg=_pooled_t), _alpha(node))))


class NDmpOlsCoefAdapter:
    """Independent leg B — DMP count via the per-probe OLS group-coefficient t (numpy lstsq).
    Equals leg A's count for a two-group design (the OLS-coef t == the pooled t)."""

    identity = "methyl-ndmp-ols"

    def execute(self, node, upstream, ctx) -> ExecValue:
        return ExecValue(value=float(_n_dmps(_per_probe_pvalues(node, leg=_ols_t), _alpha(node))))


def _all_probe_ids(ref: str) -> tuple[str, ...]:
    """Read the contract manifest's row_data feature-ids (the full probe set).
    Lighter than _load_betas — reads only the JSON manifest row_data (no betas TSV / beta matrix)."""
    se = load_contract(ref)
    betas_path = Path(se.access_methods[0].access_url)
    manifest = json.loads((betas_path.parent / f"{se.contract_uid.split('@')[0]}.json").read_text())
    return tuple(r["feature_id"] for r in manifest["row_data"])


def n_dmps_claim(
    claim_id: str,
    *,
    ref: str = "se:epicv2_casectrl_powered@1",
    probes: tuple[str, ...] | None = None,
    region: tuple[str, int, int] | None = None,
    group_col: str = "Sample_Group",
    level_a: str = "level1",
    level_b: str = "level2",
    alpha: float = 0.05,
    k: float,
    comparator: Comparator = Comparator.GE,
    oracle_ref: str | None = None,
    strength: StrengthVector | None = None,
    title: str = "n differentially-methylated probes (p < alpha)",
) -> Claim:
    """Build a PENDING claim whose plan counts DMPs (per-probe p < alpha) over the contract's probes
    (default = ALL probes) and licenses iff the count clears `k`. Mirrors region_delta_beta_claim;
    binds CANONICAL_EPICV2_V1 as the apparatus. `strength=None` -> earned at verify."""
    if probes is None:
        probes = _all_probe_ids(ref)
    if oracle_ref is None:
        oracle_ref = profile_oracle_id(CANONICAL_EPICV2_V1)
    node = OperationNode(
        id="n0",
        impl=_NDMP_IMPL,
        inputs=(DataHandle(ref=ref),),
        params=(
            ("probes", ",".join(probes)),
            ("group_col", group_col),
            ("level_a", level_a),
            ("level_b", level_b),
            ("alpha", str(alpha)),
        ),
        oracle_ref=oracle_ref,
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=float(k)),
    )
    chrom, start, end = region or ("chr1", 1_000_000, 1_004_800)
    subject = GenomicRegion(
        id=f"{chrom}:{start}-{end}", display=f"{chrom}:{start:,}-{end:,}",
        assembly="hg38", chrom=chrom, start=start, end=end,
    )
    return Claim(
        id=claim_id,
        title=title,
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="differential_methylation"),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        strength=strength,
        subject=subject,
        evaluation_plan=plan,
    )


def ndmp_independent_registry() -> AdapterRegistry:
    """Credentials asserting the two n-DMP legs are genuinely independent (distinct owners + hashes)."""
    return AdapterRegistry(credentials=(
        AdapterCredential(
            identity="methyl-ndmp-ttest",
            owner="owner-ttest",
            implementation_hash=implementation_hash_for_adapter(NDmpTTestAdapter),
        ),
        AdapterCredential(
            identity="methyl-ndmp-ols",
            owner="owner-ols",
            implementation_hash=implementation_hash_for_adapter(NDmpOlsCoefAdapter),
        ),
    ))
