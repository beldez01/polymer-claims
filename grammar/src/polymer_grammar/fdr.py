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
    retracted: bool = False               # defeat tombstone: a retracted discovery is no longer live


class FDRLedger(_Model):
    target_fdr: float = Field(gt=0.0, le=1.0)
    procedure: Literal["elond"] = "elond"
    tests: tuple[FDRTest, ...] = ()

    @property
    def n_tests(self) -> int:
        return len(self.tests)

    @property
    def n_discoveries(self) -> int:
        return sum(1 for t in self.tests if t.discovery and not t.retracted)

    @property
    def discoveries(self) -> frozenset[str]:
        return frozenset(t.claim_id for t in self.tests if t.discovery and not t.retracted)


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


def retract_tests(ledger: FDRLedger, claim_ids: Iterable[str]) -> FDRLedger:
    """Tombstone every test whose claim_id is in `claim_ids` (defeat refund): set retracted=True so
    it drops out of the live discovery count. Recorded alpha/e_value are FROZEN (never re-derived).
    Pure/immutable; a no-op (no matching live test) returns an equal-tests ledger."""
    ids = frozenset(claim_ids)
    new_tests = tuple(
        t.model_copy(update={"retracted": True}) if (t.claim_id in ids and not t.retracted) else t
        for t in ledger.tests
    )
    if new_tests == ledger.tests:
        return ledger
    return ledger.model_copy(update={"tests": new_tests})


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
