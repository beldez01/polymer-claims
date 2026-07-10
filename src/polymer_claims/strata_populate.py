"""Batch runner: turn STRATA mechanism-scan rows into pre-registered, licensable claims.
STRATA is an untrusted proposer; standing is conferred only in Task 6's run_cycle pass."""
from __future__ import annotations

import logging
import math

from polymer_grammar import Claim, Comparator, FDRLedger, MaterializationContext, Status
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

__all__ = [
    "ControlCheckFailed",
    "check_controls",
    "license_batch",
    "populate_universe",
    "preregister",
    "propose_claims",
]


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
        n_genes = getattr(r, "n_genes_tested", 1)
        if n_genes is None or not n_genes or (isinstance(n_genes, float) and math.isnan(n_genes)):
            n_genes = 1                          # missing/0/NaN -> the honest floor of 1
        claims.append(marker_drug_claim(
            f"pgx-{r.marker}-{r.drug}", ref=ref, marker=str(r.marker), drug=str(r.drug),
            drug_chebi_uri=uri,
            search_cardinality=int(n_genes), agent_id=agent_id))
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


class ControlCheckFailed(RuntimeError):
    """The publish guard: a control behaved wrong (positive did not license, or negative did)."""


def check_controls(
    corpus: Corpus, *,
    positive: str = "pgx-MTAP-Palbociclib", negative: str = "pgx-MGMT-Temozolomide",
) -> dict:
    """A read-only instrument, not a gate: reports whether the known-mechanism positive control
    licensed and the known-null negative control did not — never mutates any claim's status.
    The negative condition is "not LICENSED" (robust to the null landing PENDING as a residue OR
    terminal-REJECTED via agreed refutation — either way it is not licensed)."""
    by_id = corpus.by_id()
    pos = by_id.get(positive)
    neg = by_id.get(negative)
    positive_licensed = pos is not None and pos.status == Status.LICENSED
    negative_licensed = neg is not None and neg.status == Status.LICENSED
    return {
        "ok": positive_licensed and not negative_licensed,
        "positive_licensed": positive_licensed,
        "negative_licensed": negative_licensed,
    }


def populate_universe(
    res_df, *, ref: str, chebi_of: dict[str, str], shared_cause_factors: tuple[str, ...],
    require_controls: bool = True, agent_id: str = "strata-mechanism-v1",
) -> Corpus:
    """End-to-end: propose -> preregister -> license_batch -> check_controls (the publish guard).
    Raises ControlCheckFailed if require_controls and the control instrument reports not-ok."""
    claims = propose_claims(res_df, ref=ref, chebi_of=chebi_of, agent_id=agent_id)
    corpus = preregister(Corpus(fdr_ledger=FDRLedger(target_fdr=0.05)), claims)
    corpus = license_batch(corpus, claims, ref=ref, shared_cause_factors=shared_cause_factors)
    report = check_controls(corpus)
    if require_controls and not report["ok"]:
        raise ControlCheckFailed(f"control instrument failed: {report}")
    return corpus
