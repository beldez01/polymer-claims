"""INTEGRATE: admit graded claims, run the AGM revision contest, and reconcile defeats.

restore_consistency runs the newcomer-yields AGM contest. Phase 2.2: a LICENSED survivor grounded-OUT
this cycle is de-licensed (REJECTED) and its e-LOND discovery is refunded (tombstoned), as are any
AGM-removed claims' discoveries — so defeat and FDR are one mechanism (the ledger advance/add lives in
VERIFY; INTEGRATE does the retract). Spec docs/specs/2026-06-12-phase-2-2-defeat-evalue-refund-design.md.
"""
from __future__ import annotations

from polymer_grammar import (
    Claim,
    PendingReason,
    RejectionReason,
    Status,
    derived_rebut_edges,
    restore_consistency,
    retract_tests,
)

from .corpus import Corpus, CycleScaffolding, ExecRecord


def _merge_edges(authored, derived):
    seen = {(e.source, e.target, e.kind) for e in authored}
    out = list(authored)
    for e in derived:
        key = (e.source, e.target, e.kind)
        if key not in seen:
            seen.add(key)
            out.append(e)
    return tuple(out)


def _reject(c: Claim) -> Claim:
    """De-license a grounded-OUT survivor: flip to REJECTED + clear licensing + record the cause
    (DEFEAT_GROUNDED_OUT) so a later reinstatement can tell it from a refuted claim."""
    return Claim.model_validate(
        c.model_copy(
            update={
                "status": Status.REJECTED,
                "licensing": None,
                "pending_reason": None,
                "rejection_reason": RejectionReason.DEFEAT_GROUNDED_OUT,
            }
        ).model_dump()
    )


def _reinstate(c: Claim) -> Claim:
    """Reopen a defeat-rejected claim whose attacker has fallen (grounded-IN again) to PENDING so it
    RE-TESTS on current data — never auto-relicense a possibly-stale license. Mirrors drift.reopen_drifted."""
    return Claim.model_validate(
        c.model_copy(
            update={
                "status": Status.PENDING,
                "licensing": None,
                "pending_reason": PendingReason.REINSTATED,
                "rejection_reason": None,
            }
        ).model_dump()
    )


def integrate(
    corpus: Corpus,
    scaffolding: CycleScaffolding,
    exec_records: tuple[ExecRecord, ...],
) -> tuple[Corpus, tuple[str, ...]]:
    # 1. derived rebut edges from the post-VERIFY claims, merged with authored.
    merged = _merge_edges(corpus.defeat_edges, derived_rebut_edges(corpus.claims))
    # 2. entrenchment contest (newcomer yields per AGM).
    rr = restore_consistency(
        corpus.claims, merged, prior_in=frozenset(scaffolding.grounded_extension)
    )
    # 3. defeat = de-license + e-LOND refund (Phase 2.2). A LICENSED survivor grounded-OUT this cycle
    #    flips REJECTED; its discovery (and any AGM-removed claim's discovery) is tombstoned, so the
    #    live FDR count reflects only undefeated discoveries.
    defeated_licensed = {
        c.id for c in rr.claims if c.id in rr.flipped_out and c.status == Status.LICENSED
    }
    # Symmetric to the de-license: a defeat-rejected claim that grounded-IN again (its attacker fell)
    # reopens to PENDING to re-test. flipped_out and flipped_in are disjoint, so both apply in one pass.
    reinstated = {
        c.id for c in rr.claims
        if c.id in rr.flipped_in
        and c.status == Status.REJECTED
        and c.rejection_reason == RejectionReason.DEFEAT_GROUNDED_OUT
        and c.evaluation_plan is not None
    }
    removed = rr.retraction.possibly_retracted if rr.retraction is not None else frozenset()
    retract_ids = frozenset(defeated_licensed) | removed
    new_claims = tuple(
        _reject(c) if c.id in defeated_licensed
        else _reinstate(c) if c.id in reinstated
        else c
        for c in rr.claims
    )
    new_ledger = retract_tests(corpus.fdr_ledger, retract_ids)

    new_corpus = corpus.model_copy(
        update={"claims": new_claims, "defeat_edges": rr.edges, "fdr_ledger": new_ledger}
    )
    return new_corpus, ()
