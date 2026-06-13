"""Corpus-level online-FDR ledger — e-LOND (Phase 2.1).

e-LOND (Xu & Ramdas 2024): test t gets level α_t = target_fdr · γ_t · (D_{t-1}+1), where
γ_j = (6/π²)/j² (Σ = 1) and D_{t-1} is the discoveries so far; it is a DISCOVERY iff its
e-value e_t ≥ 1/α_t. Because the γ's sum to 1 and the e-values are valid (E[e] ≤ 1 under the
null), e-LOND controls FDR ≤ target_fdr under ARBITRARY dependence — no positive-dependence
assumption. The grammar computes the allocation + decision; e-values are supplied by the
evaluator/protocol. Standalone — no Claim coupling.
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
    e_value: float = Field(ge=0.0)        # a valid e-value (E[e] ≤ 1 under the null); no upper bound
    alpha_allocated: float                # the α_t this test was judged at
    discovery: bool                       # e_value >= 1 / alpha_allocated


class FDRLedger(_Model):
    target_fdr: float = Field(gt=0.0, le=1.0)
    procedure: Literal["elond"] = "elond"
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


def process_test(ledger: FDRLedger, claim_id: str, e_value: float) -> FDRLedger:
    """One e-LOND step. The new test gets level α_t = target_fdr · γ_t · (D_{t-1}+1) where t is its
    1-based position and D_{t-1} is the discoveries recorded so far. It is a DISCOVERY iff
    e_value ≥ 1/α_t. Returns a NEW ledger with the test appended (append-only, immutable)."""
    t = ledger.n_tests + 1
    alpha = ledger.target_fdr * _gamma(t) * (ledger.n_discoveries + 1)
    entry = FDRTest(
        index=t, claim_id=claim_id, e_value=e_value,
        alpha_allocated=alpha, discovery=e_value >= 1.0 / alpha,
    )
    return ledger.model_copy(update={"tests": ledger.tests + (entry,)})


def process_stream(ledger: FDRLedger, items: Iterable[tuple[str, float]]) -> FDRLedger:
    """Fold process_test over (claim_id, e_value) pairs in order."""
    for claim_id, e_value in items:
        ledger = process_test(ledger, claim_id, e_value)
    return ledger


def elond_decisions(
    ledger: FDRLedger, items: Iterable[tuple[str, float]]
) -> tuple[FDRLedger, dict[str, bool]]:
    """Advance the ledger over `items` in claim_id-sorted order (deterministic) and return the
    advanced ledger AND the per-claim discovery flags. Single source of truth for the VERIFY gate
    and the committed ledger."""
    ordered = sorted(items)
    advanced = process_stream(ledger, ordered)
    new_entries = advanced.tests[len(ledger.tests):]
    decisions = {t.claim_id: t.discovery for t in new_entries}
    return advanced, decisions


def is_discovery(ledger: FDRLedger, claim_id: str) -> bool:
    """True iff some recorded test for `claim_id` was a discovery."""
    return claim_id in ledger.discoveries
