"""Two INDEPENDENT legs recompute a marker->drug association over the pharmaco SE-Contract.
Leg A (mean difference of within-tissue-split AUCs; feeds the e-value) vs leg B (Hodges-Lehmann
location shift; corroborating air-gap gate). Median-split on the marker's methylation is done
WITHIN each tissue (tissue-adjusted) and is monotone-invariant (the measurement-seam requirement).
Umbrella/impure. NOT re-exported from __init__ (base import stays numpy-free)."""
from __future__ import annotations

import numpy as np
from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    Comparator,
    CompositeSubject,
    ExecValue,
    GeneOrProtein,
    GeneOrProteinIdentifiers,
    GenerationMode,
    OntologyTerm,
    OperationNode,
    PatternRef,
    PendingReason,
    Provenance,
    SatisfactionCriterion,
    Status,
    StrengthVector,
)
from polymer_grammar.oracle import ApplicabilityDomain, OracleDossier, ValidationTier
from polymer_protocol import AdapterCredential, AdapterRegistry, OracleRegistry

from .adapter_identity import implementation_hash_for_adapter
from .methyl_adapters import _load_betas

_IMPL = "pharmaco::assoc"


def _pharmaco_split(node: OperationNode) -> tuple[list[float], list[float]]:
    """(high-meth AUCs, low-meth AUCs), median-split within each tissue on marker methylation,
    pooled across tissues. Drops lines missing either value. Raises on empty groups."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    beta, sample_ids, tissue_of, p = _load_betas(node)  # tissue_of = col_data[group_col]
    marker_row, drug_row = f"meth::{p['marker']}", f"auc::{p['drug']}"
    if marker_row not in beta or drug_row not in beta:
        raise KeyError(f"missing {marker_row!r} or {drug_row!r} in contract")
    meth, auc = beta[marker_row], beta[drug_row]
    hi: list[float] = []
    lo: list[float] = []
    # group lines by tissue
    by_tissue: dict[str, list[str]] = {}
    for s in sample_ids:
        m, a = meth.get(s), auc.get(s)
        if m is None or a is None or np.isnan(m) or np.isnan(a):
            continue
        by_tissue.setdefault(tissue_of[s], []).append(s)
    for _, members in by_tissue.items():
        if len(members) < 2:
            continue
        med = float(np.median([meth[s] for s in members]))
        for s in members:
            (hi if meth[s] > med else lo).append(auc[s])
    if not hi or not lo:
        raise ValueError("empty methylation split group")
    return hi, lo


class PharmacoMeanDiffAdapter:
    """Independent leg A — mean(low-meth AUC) - mean(high-meth AUC). Positive => high-meth
    lines are more sensitive (lower AUC). Feeds the e-value."""

    identity = "pharmaco-meandiff"

    def execute(self, node, upstream, ctx) -> ExecValue:
        hi, lo = _pharmaco_split(node)
        return ExecValue(value=(sum(lo) / len(lo)) - (sum(hi) / len(hi)))


class PharmacoRankAdapter:
    """Independent leg B — Hodges-Lehmann location shift: median of all pairwise (lo_j - hi_i).
    Rank-family, robust to AUC tails; a genuinely different estimator from leg A. Corroborating
    air-gap gate (CapabilityCell.agreement_mode='both_satisfy_criterion'), never feeds the e-value."""

    identity = "pharmaco-rank"

    def execute(self, node, upstream, ctx) -> ExecValue:
        hi, lo = _pharmaco_split(node)
        h = np.asarray(hi, dtype=float)
        lo_arr = np.asarray(lo, dtype=float)
        pairwise = (lo_arr[:, None] - h[None, :]).ravel()
        return ExecValue(value=float(np.median(pairwise)))


_PHARMACO_ORACLE_ID = "gdsc_pharmaco_apparatus"


def pharmaco_oracle_id() -> str:
    return _PHARMACO_ORACLE_ID


def pharmaco_oracle_registry() -> OracleRegistry:
    """BENCHMARKED GDSC apparatus admitting the composite gene/drug subject."""
    return OracleRegistry(dossiers=(OracleDossier(
        oracle_id=_PHARMACO_ORACLE_ID, validation_tier=ValidationTier.BENCHMARKED,
        applicability_domain=ApplicabilityDomain(subject_kinds=("composite",)),
        anchor="gdsc-pharmaco-v1"),))


def pharmaco_independent_registry() -> AdapterRegistry:
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="pharmaco-meandiff", owner="owner-meandiff",
                          implementation_hash=implementation_hash_for_adapter(PharmacoMeanDiffAdapter)),
        AdapterCredential(identity="pharmaco-rank", owner="owner-rank",
                          implementation_hash=implementation_hash_for_adapter(PharmacoRankAdapter)),
    ))


def marker_drug_claim(
    claim_id: str, *, ref: str, marker: str, drug: str, drug_chebi_uri: str,
    drug_ontology: str = "CHEBI",
    tissue_adjusted: bool = True, threshold: float = 0.0, comparator: Comparator = Comparator.GT,
    search_cardinality: int, agent_id: str = "pharmaco-mechanism-v1",
    prior_cohorts: tuple[str, ...] = (), preregistration_hash: str | None = None,
    strength: StrengthVector | None = None,
) -> Claim:
    """PENDING adjusted-association claim: marker methylation is associated (tissue-adjusted) with
    drug response. Pattern adjusted_effect@v1 (association, NOT a causal edge). CategoricalLeaf
    per shipped Polymer practice; the computed AUC-difference/HL-shift lives in the verify
    result — the engine's r_adj never enters the claim. Composite (gene, drug) subject; the drug term's
    ontology defaults to CHEBI but `drug_ontology` lets an un-mapped drug use OntologyTerm's
    "other" ontology with a synthetic URI (`drug_chebi_uri` still carries the uri arg either way).
    AGENT_GENERATED. `tissue_adjusted` documents the median-split-within-tissue discipline that
    both legs enforce (via _pharmaco_split's group_col resolution) — it does not change plan shape."""
    from polymer_grammar.capability import build_evaluation_plan

    from .capabilities import PHARMACO_ASSOC_CELL

    plan = build_evaluation_plan(
        PHARMACO_ASSOC_CELL, params={"marker": marker, "drug": drug, "group_col": "Sample_Group"},
        data_ref=ref, criterion=SatisfactionCriterion(comparator=comparator, threshold=float(threshold)),
        oracle_ref=_PHARMACO_ORACLE_ID)
    subject = CompositeSubject(
        id=f"{marker}~{drug}", display=f"{marker} methylation ~ {drug} response", relation="correlational",
        parts=(
            GeneOrProtein(id=f"HGNC:{marker}", display=marker, entity_type="gene",
                          identifiers=GeneOrProteinIdentifiers(hgnc=marker, symbol=marker)),
            OntologyTerm(id=f"CHEBI:{drug}", display=drug, ontology=drug_ontology,
                         ontology_release="unknown", uri=drug_chebi_uri),
        ))
    return Claim(
        id=claim_id, title=f"{marker} methylation ~ {drug} sensitivity (tissue-adjusted)",
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term="pharmacogenomic_association"),),
        status=Status.PENDING, pending_reason=PendingReason.UNTESTED, strength=strength,
        subject=subject, evaluation_plan=plan,
        provenance=Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id=agent_id,
                              search_cardinality=int(search_cardinality),
                              preregistration_hash=preregistration_hash, prior_cohorts=prior_cohorts,
                              rationale=f"mechanism-anchored proposal: {marker} in {drug}'s target/pathway"))
