"""Batch runner: turn STRATA mechanism-scan rows into pre-registered, licensable claims.
STRATA is an untrusted proposer; standing is conferred only in Task 6's run_cycle pass."""
from __future__ import annotations

import logging

from polymer_grammar import Claim
from polymer_protocol import Corpus, register_hypotheses

from .pharmaco_adapters import marker_drug_claim

log = logging.getLogger(__name__)

__all__ = ["propose_claims", "preregister"]


def propose_claims(
    res_df, *, ref: str, chebi_of: dict[str, str], agent_id: str = "strata-mechanism-v1"
) -> list[Claim]:
    """One marker_drug_claim per scan row whose drug has a CHEBI uri. search_cardinality =
    the row's n_genes_tested (falls back to 1). Skipped-for-no-CHEBI count is logged, not silent."""
    claims: list[Claim] = []
    skipped = 0
    for r in res_df.itertuples():
        uri = chebi_of.get(str(r.drug))
        if uri is None:
            skipped += 1
            continue
        claims.append(marker_drug_claim(
            f"pgx-{r.marker}-{r.drug}", ref=ref, marker=str(r.marker), drug=str(r.drug),
            drug_chebi_uri=uri,
            search_cardinality=int(getattr(r, "n_genes_tested", 1) or 1), agent_id=agent_id))
    if skipped:
        log.warning("propose_claims: skipped %d rows lacking a CHEBI uri", skipped)
    return claims


def preregister(corpus: Corpus, claims: list[Claim]) -> Corpus:
    """Admit the proposed claims into the corpus (PENDING — no standing yet) and lock an e-LOND
    slot per claim via the protocol's register_hypotheses (which internally charges
    register_test/commitment_hash) BEFORE any e-value exists. Standing (LICENSED) is only
    conferred later by Task 6's run_cycle."""
    admitted = corpus.model_copy(update={"claims": corpus.claims + tuple(claims)})
    return register_hypotheses(admitted, claim_ids=[c.id for c in claims])
