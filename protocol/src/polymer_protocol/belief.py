"""The minimal posterior: a Beta credence a claim will license, from its StrengthVector.

Pure and deterministic (spec §3.1-3.2). No new grammar fields; reads only the existing
6-axis StrengthVector. strength=None -> Beta(1,1) (the honest know-nothing prior, which
yields maximum EIG).
"""
from __future__ import annotations

import math

from polymer_grammar import Claim

from .base import _Model
from .ledger import SelectionLedger

KAPPA_MIN = 2.0
KAPPA_MAX = 20.0
EPS = 1e-6
SETTLED_CONCENTRATION = 200.0


class Beta(_Model):
    alpha: float
    beta: float


def prior_belief(claim: Claim) -> Beta:
    s = claim.strength
    if s is None:
        return Beta(alpha=1.0, beta=1.0)
    mu = min(1.0, max(0.0, s.evidence_against_null))
    kappa = KAPPA_MIN + (KAPPA_MAX - KAPPA_MIN) * s.certainty
    alpha = max(EPS, mu * kappa)
    beta = max(EPS, kappa - mu * kappa)
    return Beta(alpha=alpha, beta=beta)


QUADRATURE_NODES = 64


def _binary_entropy_bits(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def _beta_log_pdf(t: float, alpha: float, beta: float) -> float:
    # log of t^(a-1) (1-t)^(b-1) / B(a,b)
    log_norm = math.lgamma(alpha) + math.lgamma(beta) - math.lgamma(alpha + beta)
    return (alpha - 1.0) * math.log(t) + (beta - 1.0) * math.log(1.0 - t) - log_norm


def expected_information_gain(belief: Beta) -> float:
    """Mutual information I(Y; theta) in bits between one Bernoulli outcome Y and the
    Beta credence theta. EIG = H_b(mu) - E_theta[H_b(theta)], the textbook expected
    uncertainty reduction. Deterministic fixed-node midpoint quadrature for the
    expectation (spec §3.2)."""
    a, b = belief.alpha, belief.beta
    if a + b >= SETTLED_CONCENTRATION:
        # a settled (sharply peaked) belief yields negligible expected information; return 0
        # analytically AND sidestep the fixed-node quadrature's high-concentration degradation.
        return 0.0
    mu = a / (a + b)
    # E_theta[H_b(theta)] via midpoint rule on (0,1); endpoints excluded (H_b=0 there
    # and the Beta log-pdf diverges for alpha/beta < 1).
    n = QUADRATURE_NODES
    h = 1.0 / n
    expected_cond_entropy = 0.0
    for i in range(n):
        t = (i + 0.5) * h
        expected_cond_entropy += _binary_entropy_bits(t) * math.exp(_beta_log_pdf(t, a, b)) * h
    eig = _binary_entropy_bits(mu) - expected_cond_entropy
    return max(0.0, min(1.0, eig))


def accumulated_belief(claim: Claim, ledger: SelectionLedger) -> Beta:
    """The #3a prior updated by the claim's accumulated execution outcomes (spec §3).
    Fresh claim (no ledger entry) -> the #3a prior unchanged."""
    prior = prior_belief(claim)
    o = ledger.outcome(claim.id)
    if o is None:
        return prior
    return Beta(alpha=prior.alpha + o.successes, beta=prior.beta + o.failures)
