"""Corpus-level online-FDR ledger (spec §5 #4 / unified spec §4).

A first-class, immutable IR entity controlling the false-discovery rate over an
open-ended stream of significance tests, via LOND (Levels based On Number of Discoveries,
Javanmard & Montanari 2018): test t gets level α_t = target_fdr · γ_t · (D_{t-1} + 1),
where γ_j = (6/π²)/j² (Σ = 1) and D_{t-1} is the number of discoveries so far. The grammar
computes the allocation; p-values are supplied by the evaluator/protocol. Standalone — no
Claim coupling; imports nothing from polymer_formalclaim.
"""
from __future__ import annotations

import math


def _gamma(j: int) -> float:
    """LOND discount γ_j = (6/π²)/j² for j ≥ 1 (non-negative, monotone decreasing, Σ = 1)."""
    return (6.0 / math.pi**2) / (j * j)
