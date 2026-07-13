"""Phase 2.1: the native e-value for an apparatus claim + the per-claim evidence map.

`betting_evalue` is the Waudby-Smith & Ramdas (JRSS-B 2024, Eqs. 24-26) betting / empirical-Bernstein
e-value for the severe-test composite one-sided null H0: (mu_B - mu_A) <= threshold, over per-sample
region-mean betas bounded in [0,1]. Exactly valid from BOUNDEDNESS ALONE (Ville's inequality on a
predictable-lambda test supermartingale) — no Gaussianity; variance-adaptive; finite at zero variance.
`evidence_map` resolves each apparatus claim's per-sample betas (impure: load_contract via
_region_group_means) and computes its e-value.
"""
from __future__ import annotations

import numpy as np

from polymer_grammar import Comparator, DataHandle
from polymer_protocol.corpus import Corpus

from .background_enrichment import _ENRICH_IMPL, _bg_rate
from .methyl_adapters import _IMPL, _region_group_means
from .methyl_ndmp import _NDMP_IMPL, _alpha, dmp_indicators

# c<1 caps the betting fraction so every capital factor (1 + lam*W) stays strictly positive (Eq.25);
# 0.9 recovers power while keeping factors >= 1-c = 0.1. Fixed, data-independent.
_C = 0.9
# A small fixed set of pairing seeds; averaging e-values preserves E[e] <= 1 (convex combination) and
# stabilizes the random index-pairing. Fixed -> the e-value is deterministic given the data.
_SEEDS = (0, 1, 2, 3)


def _grapa_capital(W: np.ndarray, lam_max: float) -> float:
    """The shared GRAPA betting-capital process e = prod_i (1 + lam_i * W_i), where lam_i is the
    predictable (PAST-ONLY) plug-in floored at 0 (one-sided) and capped at lam_max. Order-dependent
    (the caller fixes W's order). Float ops are kept in their exact order to preserve results."""
    e, s, s2, cnt = 1.0, 0.0, 0.0, 0
    for i in range(len(W)):
        if cnt > 0:                                           # estimates use ONLY prior points 0..i-1
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
    return _grapa_capital(W, lam_max)


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


def _capital_onesample(x: np.ndarray, p0: float, seed: int) -> float:
    """One betting capital process e = prod_i (1 + lam_i * W_i) for H0: E[X] <= p0 over X in {0,1}.
    W_i = X_i - p0 (so E[W] <= 0 under H0); lam_i is the predictable (PAST-ONLY) GRAPA plug-in, floored
    at 0 (one-sided) and capped so every factor stays positive (the most negative W is -p0)."""
    rng = np.random.default_rng(seed)
    n = len(x)
    # shuffle observation order so the seed-average is over orderings (the betting process is order-dependent)
    W = (x - p0)[rng.permutation(n)]
    lam_max = _C / p0  # positivity: 1 + lam*(-p0) > 0 needs lam < 1/p0; _C<1 keeps factors >= 1-_C
    return _grapa_capital(W, lam_max)


def count_enrichment_evalue(indicators, *, p0: float) -> float:
    """Valid e-value for H0: the per-probe DMP-rate <= p0, over Bernoulli DMP-indicators X in {0,1}.
    A one-sample WSR betting / Ville e-value (same family as betting_evalue, on bounded data): tests
    whether the observed DMP count is ENRICHED beyond the chance rate p0 (= the per-probe alpha).
    Seed-averaged -> deterministic. Empty -> 1.0."""
    x = np.asarray(indicators, dtype=float)
    if x.size == 0:
        return 1.0
    es = [_capital_onesample(x, p0, s) for s in _SEEDS]
    return float(sum(es) / len(es))


def _terminal_node(claim):
    plan = claim.evaluation_plan
    if plan is None:
        return None
    g = plan.graph
    return next((n for n in g.nodes if n.id == g.terminal), None)


def evidence_map(corpus: Corpus) -> dict[str, float]:
    """Per-claim native e-value keyed by claim id. region-Δβ (impl _IMPL) -> betting_evalue on the
    group-mean diff; n-DMPs (impl _NDMP_IMPL) -> count_enrichment_evalue on the DMP indicators. Any other
    claim gets NO entry (caller falls back to the 3-way gate). Impure: reads the bundled contract."""
    out: dict[str, float] = {}
    for c in corpus.claims:
        node = _terminal_node(c)
        if node is None:
            continue
        if not any(isinstance(i, DataHandle) for i in node.inputs):
            continue
        crit = c.evaluation_plan.criterion
        if crit.threshold is None or crit.comparator not in (
            Comparator.GT, Comparator.GE, Comparator.LT, Comparator.LE
        ):
            continue
        if node.impl == _IMPL:
            try:
                a, b = _region_group_means(node)
            except (FileNotFoundError, KeyError, ValueError):
                continue
            out[c.id] = betting_evalue(a, b, threshold=crit.threshold, comparator=crit.comparator)
        elif node.impl == _NDMP_IMPL:
            try:
                indicators = dmp_indicators(node)
                p0 = _alpha(node)
                # inside the try (and catch ZeroDivisionError) so a bad p0 (e.g. alpha=0,
                # which divides by zero in the e-value) skips the claim like other bad contracts
                out[c.id] = count_enrichment_evalue(indicators, p0=p0)
            except (FileNotFoundError, KeyError, ValueError, ZeroDivisionError):
                continue
        elif node.impl == _ENRICH_IMPL:
            try:
                # SAME count-enrichment e-value as n-DMP, but the null is the matched-BACKGROUND rate
                # (p0 = bg_rate_ttest, the pre-registered t-leg background) instead of chance (alpha).
                # Leg-A view (dmp_indicators, pooled-t) matches EnrichmentTTestAdapter's DMP call.
                out[c.id] = count_enrichment_evalue(dmp_indicators(node),
                                                    p0=_bg_rate(node, "bg_rate_ttest"))
            except (FileNotFoundError, KeyError, ValueError, ZeroDivisionError):
                continue
    return out
