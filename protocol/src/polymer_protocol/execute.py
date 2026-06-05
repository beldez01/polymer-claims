"""EXECUTE/GROUND: run the Phase-8 air-gapped gate over committed, non-gated claims.

Reuses evaluate.verify() — the two-implementation agreement gate that mints a Satisfaction
only on cross-adapter agreement + SATISFIED (no self-licensing). Produces evidence
(ExecRecords); writes no status (VERIFY decides). Caller must supply >=2 distinct-identity
adapters or verify() raises SelfLicensingError. Spec §6.5.
"""
from __future__ import annotations

from polymer_grammar import (
    Adapter,
    Claim,
    MaterializationContext,
    Status,
    requires_safety_review,
    verify,
)

from .corpus import Corpus, ExecRecord, is_locked


def _is_executable(claim: Claim) -> bool:
    if claim.status != Status.PENDING or claim.evaluation_plan is None:
        return False
    # committed: carries a preregistration lock (from COMMIT)
    if not is_locked(claim):
        return False
    # not safety-gated (same predicate SAFETY uses)
    if claim.governance is not None and requires_safety_review(claim.governance):
        return False
    return True


def execute_ground(
    corpus: Corpus,
    adapters: tuple[Adapter, ...],
    ctx: MaterializationContext,
    only: frozenset[str] | None = None,
) -> tuple[Corpus, tuple[ExecRecord, ...]]:
    """Run verify() over executable claims, optionally gated to this cycle's selection.

    When ``only`` is provided, a claim additionally must be in that set to execute: the
    permanent preregistration lock alone is no longer sufficient (it stays for anti-HARKing,
    but execution is gated to the selected set). ``only=None`` runs all executable claims.
    """
    records = []
    for c in corpus.claims:
        if only is not None and c.id not in only:
            continue
        if not _is_executable(c):
            continue
        evaluation = verify(c.evaluation_plan, ctx, adapters, claim_leaves=c.leaves)
        records.append(ExecRecord(claim_id=c.id, evaluation=evaluation))
    return corpus, tuple(records)
