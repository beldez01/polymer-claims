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
from collections.abc import Iterable
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


def process_test(ledger: FDRLedger, claim_id: str, p_value: float) -> FDRLedger:
    """One LOND step. The new test gets level α_t = target_fdr · γ_t · (D_{t-1}+1) where
    t is its 1-based position and D_{t-1} is the discoveries recorded in `ledger` so far.
    It's a discovery iff p_value <= α_t. Returns a NEW ledger with the test appended
    (append-only, immutable)."""
    t = ledger.n_tests + 1
    alpha = ledger.target_fdr * _gamma(t) * (ledger.n_discoveries + 1)
    entry = FDRTest(
        index=t, claim_id=claim_id, p_value=p_value,
        alpha_allocated=alpha, discovery=p_value <= alpha,
    )
    return ledger.model_copy(update={"tests": ledger.tests + (entry,)})


def process_stream(
    ledger: FDRLedger, items: Iterable[tuple[str, float]]
) -> FDRLedger:
    """Fold process_test over (claim_id, p_value) pairs in order. Each step sees the
    discoveries of the prior steps (so the result equals iterated process_test)."""
    for claim_id, p_value in items:
        ledger = process_test(ledger, claim_id, p_value)
    return ledger


def is_discovery(ledger: FDRLedger, claim_id: str) -> bool:
    """True iff some recorded test for `claim_id` was a discovery. The protocol uses this
    to gate licensing; keeps the ledger decoupled from Claim."""
    return claim_id in ledger.discoveries
