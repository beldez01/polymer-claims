"""INTEGRATE: admit graded claims, run the AGM revision contest, and reconcile defeats.

restore_consistency runs the newcomer-yields AGM contest. Phase 2.2: a LICENSED survivor grounded-OUT
this cycle is de-licensed (REJECTED) and its e-LOND discovery is refunded (tombstoned), as are any
AGM-removed claims' discoveries — so defeat and FDR are one mechanism (the ledger advance/add lives in
VERIFY; INTEGRATE does the retract). Spec docs/specs/2026-06-12-phase-2-2-defeat-evalue-refund-design.md.
"""
from __future__ import annotations

from polymer_grammar import (
    Claim,
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
    """De-license a grounded-OUT survivor: flip to REJECTED + clear licensing (mirrors VERIFY's
    grounded-OUT path; re-validates so the licensing-only-when-LICENSED invariant holds)."""
    return Claim.model_validate(
        c.model_copy(
            update={"status": Status.REJECTED, "licensing": None, "pending_reason": None}
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
    removed = rr.retraction.possibly_retracted if rr.retraction is not None else frozenset()
    retract_ids = frozenset(defeated_licensed) | removed
    new_claims = tuple(_reject(c) if c.id in defeated_licensed else c for c in rr.claims)
    new_ledger = retract_tests(corpus.fdr_ledger, retract_ids)

    new_corpus = corpus.model_copy(
        update={"claims": new_claims, "defeat_edges": rr.edges, "fdr_ledger": new_ledger}
    )
    return new_corpus, ()
