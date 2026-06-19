"""REGISTER stage (Phase D): pre-register hypotheses BEFORE execution. Each claim with an
evaluation_plan advances the e-LOND stream and locks its α (register_test) — the commit-before-data
step that makes q honest under an autonomous agent. Pure; Corpus stays 4 (registration lives in
fdr_ledger). Claims already pending or planless are skipped (no double-charge)."""
from __future__ import annotations

from collections.abc import Iterable

from polymer_grammar import register_test
from polymer_grammar.commitment import commitment_hash

from .corpus import Corpus, SelectionRecord


def register_hypotheses(corpus: Corpus, claim_ids: Iterable[str] | None = None) -> Corpus:
    by_id = {c.id: c for c in corpus.claims}
    targets = sorted(by_id) if claim_ids is None else sorted(set(claim_ids) & set(by_id))
    pending = {t.claim_id for t in corpus.fdr_ledger.tests if t.e_value is None and not t.retracted}
    ledger = corpus.fdr_ledger
    for cid in targets:
        claim = by_id[cid]
        if claim.evaluation_plan is None or cid in pending:
            continue
        ledger = register_test(ledger, cid, commitment_hash(claim))
    if ledger == corpus.fdr_ledger:
        return corpus
    return corpus.model_copy(update={"fdr_ledger": ledger})


def register_selected(
    corpus: Corpus, record: SelectionRecord, *, k: int | None = None
) -> Corpus:
    """Budget-aware incubation commit: register (e-LOND slot, slice-1 register_test) only the
    SELECT-selected claims, in rank order, optionally truncated to top-k. Non-selected/incubated
    candidates are NOT charged — honest because SELECT ranking is data-blind (it did not peek at
    the outcome)."""
    ranked = [
        d.claim_id for d in sorted(record.decisions, key=lambda d: d.rank) if d.selected
    ]
    if k is not None:
        ranked = ranked[:k]
    return register_hypotheses(corpus, ranked)
