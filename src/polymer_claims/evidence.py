"""Phase 2.1: the native e-value for an apparatus claim + the per-claim evidence map.

`betting_evalue` is the Waudby-Smith & Ramdas (JRSS-B 2024, Eqs. 24-26) betting / empirical-Bernstein
e-value for the severe-test composite one-sided null H0: (mu_B - mu_A) <= threshold, over per-sample
region-mean betas bounded in [0,1]. Exactly valid from BOUNDEDNESS ALONE (Ville's inequality on a
predictable-lambda test supermartingale) — no Gaussianity; variance-adaptive; finite at zero variance.
`evidence_map` resolves each apparatus claim's per-sample betas (impure: load_contract via
_region_group_means) and computes its e-value. See docs/specs/2026-06-12-phase-2-1-evalue-fdr-verify-design.md.
"""
from __future__ import annotations

import numpy as np

from polymer_grammar import Comparator

# c<1 caps the betting fraction so every capital factor (1 + lam*W) stays strictly positive (Eq.25);
# 0.9 recovers power while keeping factors >= 1-c = 0.1. Fixed, data-independent.
_C = 0.9
# A small fixed set of pairing seeds; averaging e-values preserves E[e] <= 1 (convex combination) and
# stabilizes the random index-pairing. Fixed -> the e-value is deterministic given the data.
_SEEDS = (0, 1, 2, 3)


def _capital(a: np.ndarray, b: np.ndarray, theta0: float, seed: int) -> float:
    """One betting capital process e = prod_i (1 + lam_i * W_i) for H0: E[b-a] <= theta0.
    lam_i is the predictable (PAST-ONLY) GRAPA plug-in, capped to keep factors positive."""
    rng = np.random.default_rng(seed)
    n = min(len(a), len(b))
    ia = rng.permutation(len(a))[:n]
    ib = rng.permutation(len(b))[:n]
    w = np.clip(b[ib], 0.0, 1.0) - np.clip(a[ia], 0.0, 1.0)   # paired diffs in [-1, 1]
    W = (w - theta0)[rng.permutation(n)]                      # shift: E[W] <= 0 under H0
    lam_max = _C / (1.0 + abs(theta0))                        # positivity cap (Eq.25)
    e, s, s2, cnt = 1.0, 0.0, 0.0, 0
    for i in range(n):
        if cnt > 0:                                           # estimates use ONLY points 1..i-1
            mu = s / cnt
            var = max(s2 / cnt - mu * mu, 0.0)
        else:
            mu, var = 0.0, 0.25                               # padded variance-1/4 prior (Eq.26)
        denom = var + mu * mu
        lam = mu / denom if denom > 0.0 else 0.0              # GRAPA fraction
        lam = min(max(lam, 0.0), lam_max)                     # one-sided (>=0) + positivity cap
        e *= 1.0 + lam * float(W[i])                          # capital update (Eq.24)
        s += float(W[i])
        s2 += float(W[i]) ** 2
        cnt += 1
    return e


def betting_evalue(
    a, b, *, threshold: float, comparator: Comparator
) -> float:
    """Valid e-value for the severe-test null that the region effect does NOT clear `threshold`.
    GT/GE tests mu_b - mu_a > threshold; LT/LE is the mirror (swap groups, negate threshold).
    Averaged over a fixed seed set -> deterministic. EQ/NE/WITHIN_TOL -> 0.0 (no one-sided test)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0:
        return 0.0
    if comparator in (Comparator.GT, Comparator.GE):
        ga, gb, theta0 = a, b, threshold
    elif comparator in (Comparator.LT, Comparator.LE):
        ga, gb, theta0 = b, a, -threshold
    else:
        return 0.0
    es = [_capital(ga, gb, theta0, s) for s in _SEEDS]
    return float(sum(es) / len(es))
