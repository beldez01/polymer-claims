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
from typing import Literal

from pydantic import Field

from .base import _Model


def _gamma(j: int) -> float:
    """LOND discount γ_j = (6/π²)/j² for j ≥ 1 (non-negative, monotone decreasing, Σ = 1)."""
    return (6.0 / math.pi**2) / (j * j)


class FDRTest(_Model):
    index: int                            # 1-based position in the test stream
    claim_id: str
    p_value: float = Field(ge=0.0, le=1.0)
    alpha_allocated: float                # the α_t this test was judged at (may exceed 1 if budget is large)
    discovery: bool                       # p_value <= alpha_allocated


class FDRLedger(_Model):
    target_fdr: float = Field(gt=0.0, le=1.0)
    procedure: Literal["lond"] = "lond"
    tests: tuple[FDRTest, ...] = ()

    @property
    def n_tests(self) -> int:
        return len(self.tests)

    @property
    def n_discoveries(self) -> int:
        return sum(1 for t in self.tests if t.discovery)

    @property
    def discoveries(self) -> frozenset[str]:
        return frozenset(t.claim_id for t in self.tests if t.discovery)
