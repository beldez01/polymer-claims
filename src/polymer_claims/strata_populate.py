"""Batch runner: turn STRATA mechanism-scan rows into pre-registered, licensable claims.
STRATA is an untrusted proposer; standing is conferred only in Task 6's run_cycle pass."""
from __future__ import annotations

import logging

from polymer_grammar import Claim, Comparator, MaterializationContext
from polymer_protocol import Corpus, register_hypotheses, run_cycle

from .capabilities import CAPABILITY_CELLS
from .contracts import load_contract
from .evidence import _terminal_node
from .pharmaco_adapters import (
    PharmacoMeanDiffAdapter,
    PharmacoRankAdapter,
    marker_drug_claim,
    pharmaco_independent_registry,
    pharmaco_oracle_registry,
)
from .pharmaco_evidence import pharmaco_evalue

log = logging.getLogger(__name__)

__all__ = ["propose_claims", "preregister", "license_batch"]


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


def _evidence_for(claims: list[Claim], *, threshold: float = 0.0) -> dict[str, float]:
    """Per-claim e-value from leg A's within-tissue methylation split (ONE leg — the rank leg is
    the corroborating air-gap gate, never a factor). Skips claims whose contract read fails."""
    out: dict[str, float] = {}
    for c in claims:
        node = _terminal_node(c)
        if node is None:
            continue
        try:
            out[c.id] = pharmaco_evalue(node, threshold=threshold, comparator=Comparator.GT)
        except (FileNotFoundError, KeyError, ValueError):
            continue
    return out


def license_batch(
    corpus: Corpus, claims: list[Claim], *, ref: str, shared_cause_factors: tuple[str, ...]
) -> Corpus:
    """Confer standing on a pre-registered batch: run the two independent legs + registry + oracle
    + per-claim e-values through run_cycle against cohort `ref`. Every materialization carries
    `shared_cause_factors` (the GDSC-shared causes), so any later cross-cohort replication is gated
    by §E (cohorts_error_independent) rather than silently minting REPLICATED. Within-GDSC claims
    live in a SINGLE cohort, so a licensed claim resolves to IndependenceTier.REPRODUCED; a claim
    whose e-value never clears the e-LOND discovery bar stays PENDING (residue, not rejected).

    Mirrors the run_cycle wiring proven in real_kernel_proof.py / _ndmp_gate.run_ndmp_gate: the
    caller owns contract-root scoping (load_contract + the adapters read the active root)."""
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    try:
        dimnames_hash = load_contract(ref).dimnames_hash
    except FileNotFoundError:
        dimnames_hash = None
    factors = tuple(shared_cause_factors)
    materializations = {
        c.id: MaterializationContext(
            id=base.id, api_version=base.api_version, data_version=base.data_version,
            dimnames_hash=dimnames_hash, shared_cause_factors=factors)
        for c in claims if _terminal_node(c) is not None
    }
    result = run_cycle(
        corpus, (PharmacoMeanDiffAdapter(), PharmacoRankAdapter()), base,
        adapter_registry=pharmaco_independent_registry(),
        oracles=pharmaco_oracle_registry(),
        materializations=materializations,
        evidence=_evidence_for(claims),
        capability_registry=CAPABILITY_CELLS)
    return result.corpus
