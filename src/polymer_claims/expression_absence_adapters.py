"""expression::absence — the healthy-tissue safety-veto capability (Ch2 GTEx safety atlas).

The INVERSE of expression::floor: a target's UPPER summary across healthy tissues must clear (stay
below) a pre-registered ceiling. Two INDEPENDENT legs return an upper summary — Leg A = max (the
worst tissue), Leg B = high quantile (rank-family) — and the LE criterion licenses iff BOTH are
<= ceiling, so a single healthy tissue above the ceiling vetoes. The between-tissue discrimination is
carried by expression_absence_evidence, not the leaf. Umbrella/impure (reads the contract via
methyl_adapters._load_betas); NOT re-exported from __init__ (base import stays numpy-free).
"""
from __future__ import annotations

import numpy as np
from polymer_grammar import ExecValue, OperationNode
from polymer_grammar.oracle import ApplicabilityDomain, OracleDossier, ValidationTier
from polymer_protocol import AdapterCredential, AdapterRegistry, OracleRegistry

from .adapter_identity import implementation_hash_for_adapter
from .methyl_adapters import _load_betas

_IMPL = "expression::absence"
_ORACLE_ID = "expression_absence_apparatus"
_Q_DEFAULT = 0.99


def _tissue_values(node: OperationNode) -> list[float]:
    """All non-NaN expression values of the target's ``expr::<gene>`` row across healthy tissues.
    Groups are irrelevant to a safety veto — the summary is over every sample/tissue in the atlas."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    beta, sample_ids, _group_of, p = _load_betas(node)
    row = f"expr::{p['gene']}"
    if row not in beta:
        raise KeyError(f"missing {row!r} in contract")
    vals = [
        float(v)
        for s in sample_ids
        if (v := beta[row].get(s)) is not None and not np.isnan(v)
    ]
    if not vals:
        raise ValueError("no expression values for absence")
    return vals


def _high_quantile(xs, q: float = _Q_DEFAULT) -> float:
    """The q-quantile upper summary (default 99th percentile) — robust to a single noisy tissue."""
    return float(np.quantile(np.asarray(list(xs), dtype=float), q))


class ExpressionAbsenceMaxAdapter:
    """Leg A — the worst tissue (max). The extreme upper summary; carries the hard veto under LE."""

    identity = "expr-absence-max"

    def execute(self, node, upstream, ctx) -> ExecValue:
        return ExecValue(value=float(max(_tissue_values(node))))


class ExpressionAbsenceRankQAdapter:
    """Leg B — the high-quantile (q99) upper summary. Rank-family; an independent estimator of the
    upper tail from Leg A's max (the axis of operationalization that makes their agreement meaningful)."""

    identity = "expr-absence-rankq"

    def execute(self, node, upstream, ctx) -> ExecValue:
        return ExecValue(value=_high_quantile(_tissue_values(node), q=_Q_DEFAULT))


def expression_absence_oracle_id() -> str:
    return _ORACLE_ID


def expression_absence_oracle_registry() -> OracleRegistry:
    return OracleRegistry(dossiers=(OracleDossier(
        oracle_id=_ORACLE_ID, validation_tier=ValidationTier.BENCHMARKED,
        applicability_domain=ApplicabilityDomain(subject_kinds=("gene_or_protein",)),
        anchor="gtex-healthy-expr-v1"),))


def expression_absence_registry() -> AdapterRegistry:
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="expr-absence-max", owner="owner-expr-absence-max",
                          implementation_hash=implementation_hash_for_adapter(ExpressionAbsenceMaxAdapter)),
        AdapterCredential(identity="expr-absence-rankq", owner="owner-expr-absence-rankq",
                          implementation_hash=implementation_hash_for_adapter(ExpressionAbsenceRankQAdapter)),
    ))
