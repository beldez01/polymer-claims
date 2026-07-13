"""Two INDEPENDENT legs estimate the fusion+ group's expression location over the fusion-expression
SE-contract; the criterion checks each clears the pre-registered floor. Leg A = mean, Leg B =
Hodges-Lehmann pseudo-median (rank-family). Named-categorical split on Sample_Group. Umbrella/impure;
NOT re-exported from __init__ (base import stays numpy-free)."""
from __future__ import annotations

import numpy as np
from polymer_grammar import (
    Claim,
    Comparator,
    ExecValue,
    GeneOrProtein,
    GeneOrProteinIdentifiers,
    GenerationMode,
    OperationNode,
    PendingReason,
    Provenance,
    QuantityLeaf,
    SatisfactionCriterion,
    Status,
    StrengthVector,
)
from polymer_grammar.leaf import MeasurementBasis, MeasurementContext
from polymer_grammar.oracle import ApplicabilityDomain, OracleDossier, ValidationTier
from polymer_protocol import AdapterCredential, AdapterRegistry, OracleRegistry

from .adapter_identity import implementation_hash_for_adapter
from .methyl_adapters import _load_betas

_IMPL = "expression::floor"
_ORACLE_ID = "expression_floor_apparatus"


def _expr_split(node: OperationNode) -> tuple[list[float], list[float]]:
    """(fusion_pos TPMs, fusion_neg TPMs) — named-categorical split on Sample_Group. Drops NaN.
    Raises on empty group."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    beta, sample_ids, group_of, p = _load_betas(node)   # group_of = col_data[group_col]
    row = f"expr::{p['gene']}"
    if row not in beta:
        raise KeyError(f"missing {row!r} in contract")
    vals = beta[row]
    a_lvl, b_lvl = p["level_a"], p["level_b"]
    pos: list[float] = []
    neg: list[float] = []
    for s in sample_ids:
        v = vals.get(s)
        if v is None or np.isnan(v):
            continue
        g = group_of[s]
        if g == a_lvl:
            pos.append(float(v))
        elif g == b_lvl:
            neg.append(float(v))
    if not pos or not neg:
        raise ValueError("empty fusion split group")
    return pos, neg


def _hodges_lehmann(xs: list[float]) -> float:
    """One-sample HL pseudo-median: median of Walsh averages (x_i + x_j)/2, i<=j."""
    a = np.asarray(xs, dtype=float)
    walsh = ((a[:, None] + a[None, :]) / 2.0)[np.triu_indices(len(a))]
    return float(np.median(walsh))


class ExpressionFloorMeanAdapter:
    """Leg A — mean of fusion_pos TPM. Independent estimator of the group location."""
    identity = "expr-floor-mean"

    def execute(self, node, upstream, ctx) -> ExecValue:
        pos, _ = _expr_split(node)
        return ExecValue(value=float(np.mean(pos)))


class ExpressionFloorHLAdapter:
    """Leg B — Hodges-Lehmann pseudo-median of fusion_pos TPM. Rank-family; independent of leg A."""
    identity = "expr-floor-hl"

    def execute(self, node, upstream, ctx) -> ExecValue:
        pos, _ = _expr_split(node)
        return ExecValue(value=_hodges_lehmann(pos))


def expression_floor_oracle_id() -> str:
    return _ORACLE_ID


def expression_floor_oracle_registry() -> OracleRegistry:
    return OracleRegistry(dossiers=(OracleDossier(
        oracle_id=_ORACLE_ID, validation_tier=ValidationTier.BENCHMARKED,
        applicability_domain=ApplicabilityDomain(subject_kinds=("gene_or_protein",)),
        anchor="tcga-laml-fusion-expr-v1"),))


def expression_floor_registry() -> AdapterRegistry:
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="expr-floor-mean", owner="owner-expr-mean",
                          implementation_hash=implementation_hash_for_adapter(ExpressionFloorMeanAdapter)),
        AdapterCredential(identity="expr-floor-hl", owner="owner-expr-hl",
                          implementation_hash=implementation_hash_for_adapter(ExpressionFloorHLAdapter)),
    ))


def expression_floor_claim(
    claim_id: str, *, ref: str, gene: str, floor: float, tissue: str,
    level_a: str = "fusion_pos", level_b: str = "fusion_neg",
    search_cardinality: int, agent_id: str = "expression-floor-v1",
    prior_cohorts: tuple[str, ...] = (), preregistration_hash: str | None = None,
    strength: StrengthVector | None = None,
) -> Claim:
    """PENDING claim: `gene` expression in the fusion_pos group clears `floor` TPM (a GAP-3 floor
    on a QuantityLeaf) and fusion_neg does not (carried by the discrimination e-value, not this
    leaf). The COMPUTED level never enters the leaf — the leaf carries the pre-registered floor."""
    from polymer_grammar.capability import build_evaluation_plan

    from .expression_floor_patterns import EXPRESSION_FLOOR  # Task 3
    from .capabilities import EXPRESSION_FLOOR_CELL           # Task 3

    plan = build_evaluation_plan(
        EXPRESSION_FLOOR_CELL,
        params={"gene": gene, "group_col": "Sample_Group", "level_a": level_a, "level_b": level_b},
        data_ref=ref,
        criterion=SatisfactionCriterion(comparator=Comparator.GE, reference_leaf_index=0),
        oracle_ref=_ORACLE_ID)
    leaf = QuantityLeaf(value=float(floor), low=float(floor),
                        measurement_basis=MeasurementBasis.DERIVED,
                        formula="fusion_pos_group_expression >= floor_tpm",
                        context=MeasurementContext(tissue=tissue, assay="RNA-seq TPM"))
    subject = GeneOrProtein(id=f"HGNC:{gene}", display=gene, entity_type="gene",
                            identifiers=GeneOrProteinIdentifiers(hgnc=gene, symbol=gene))
    return Claim(
        id=claim_id, title=f"{gene} clears the {floor:g} TPM expression floor in {tissue} ({level_a})",
        pattern=EXPRESSION_FLOOR, leaves=(leaf,),
        status=Status.PENDING, pending_reason=PendingReason.UNTESTED, strength=strength,
        subject=subject, evaluation_plan=plan,
        provenance=Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id=agent_id,
                              search_cardinality=int(search_cardinality),
                              preregistration_hash=preregistration_hash, prior_cohorts=prior_cohorts,
                              rationale=f"fusion-driven re-expression floor: {gene} in {tissue}"))
