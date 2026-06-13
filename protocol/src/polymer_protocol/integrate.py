"""INTEGRATE: admit graded claims and run the AGM revision contest.

Recomputes derived rebut edges and runs restore_consistency (newcomer yields per AGM).
The FDR ledger is now advanced in VERIFY (Phase 2.1: licensing owns the e-LOND ledger).
Duhem blame needs protocol-supplied BlameSets (no input surface in the spine Corpus) and
is deferred to #4/#5. Spec §6.7.
"""
from __future__ import annotations

from polymer_grammar import derived_rebut_edges, restore_consistency

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
    # NOTE: the FDR ledger is now advanced in VERIFY (Phase 2.1: licensing owns the e-LOND ledger).
    new_corpus = corpus.model_copy(update={"claims": rr.claims, "defeat_edges": rr.edges})
    return new_corpus, ()
