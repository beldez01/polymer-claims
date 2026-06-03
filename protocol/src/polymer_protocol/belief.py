"""The minimal posterior: a Beta credence a claim will license, from its StrengthVector.

Pure and deterministic (spec §3.1-3.2). No new grammar fields; reads only the existing
6-axis StrengthVector. strength=None -> Beta(1,1) (the honest know-nothing prior, which
yields maximum EIG).
"""
from __future__ import annotations

from polymer_grammar import Claim

from .base import _Model

KAPPA_MIN = 2.0
KAPPA_MAX = 20.0
EPS = 1e-6


class Beta(_Model):
    alpha: float
    beta: float


def prior_belief(claim: Claim) -> Beta:
    s = claim.strength
    if s is None:
        return Beta(alpha=1.0, beta=1.0)
    mu = min(1.0, max(0.0, s.evidence_against_null))
    kappa = KAPPA_MIN + (KAPPA_MAX - KAPPA_MIN) * (1.0 - s.uncertainty)
    alpha = max(EPS, mu * kappa)
    beta = max(EPS, kappa - mu * kappa)
    return Beta(alpha=alpha, beta=beta)
