"""INTEGRATE: admit graded claims, run the AGM revision contest, advance the FDR ledger.

Recomputes derived rebut edges, runs restore_consistency (newcomer yields per AGM), and
processes one online-FDR test per executed claim using its executed terminal value as the
p-value. Duhem blame needs protocol-supplied BlameSets (no input surface in the spine
Corpus) and is deferred to #4/#5. Spec §6.7.
"""
from __future__ import annotations

from polymer_grammar import derived_rebut_edges, process_test, restore_consistency

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


def _terminal_value(record: ExecRecord):
    results = record.evaluation.results
    if not results:
        return None
    return results[0].terminal.value


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

    # 3. online-FDR: one test per executed claim, deterministic order, valid p-values only.
    ledger = corpus.fdr_ledger
    skipped = []
    for rec in sorted(exec_records, key=lambda r: r.claim_id):
        val = _terminal_value(rec)
        if isinstance(val, (int, float)) and not isinstance(val, bool) and 0.0 <= val <= 1.0:
            ledger = process_test(ledger, rec.claim_id, float(val))
        else:
            skipped.append(rec.claim_id)

    new_corpus = corpus.model_copy(
        update={"claims": rr.claims, "defeat_edges": rr.edges, "fdr_ledger": ledger}
    )
    return new_corpus, tuple(skipped)
