"""n-DMPs-at-FDR: the count of differentially-methylated probes (a probe is a DMP iff its per-probe
two-group pooled t-test p-value < alpha), as a second scalar reduction alongside region-Δβ. Two
independent legs compute the per-probe t two ways (manual pooled-t vs OLS-coef t) and AGREE on the
integer count -> air-gap. Umbrella/impure (reads the contract via _load_betas). NOT re-exported from
__init__ (base import stays numpy-free). The count's e-value (count_enrichment_evalue) lives in
evidence.py. See docs/superpowers/specs/2026-06-14-n-dmps-at-fdr-design.md.
"""
from __future__ import annotations

import math

import numpy as np
from polymer_grammar import OperationNode

from .methyl_adapters import _load_betas

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
