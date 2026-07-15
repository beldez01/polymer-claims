"""Pre-register + license the expression::absence safety-veto spine through run_cycle (Ch2 GTEx
safety atlas). Reuses the generic `preregister` / `check_controls` from expression_floor_populate;
mirrors its per-claim-isolation `license_batch` (the reference_leaf criterion + select_stage
cardinality reasoning is identical). Only the adapters/registry/oracle/evidence and the
claim-construction are swapped. Umbrella/impure ([spine] extra); NOT re-exported from __init__."""
from __future__ import annotations

from polymer_grammar import Claim, MaterializationContext
from polymer_protocol import Corpus, run_cycle

from .capabilities import CAPABILITY_CELLS
from .contracts import load_contract
from .evidence import _terminal_node
from .expression_absence_adapters import (
    ExpressionAbsenceMaxAdapter,
    ExpressionAbsenceRankQAdapter,
    _tissue_values,
    expression_absence_claim,
    expression_absence_oracle_registry,
    expression_absence_registry,
)
from .expression_absence_evidence import expression_absence_evalue
from .expression_floor_populate import check_controls, preregister  # generic over claims

__all__ = [
    "check_controls",
    "license_batch",
    "preregister",
    "propose_safety_claims",
]


def propose_safety_claims(ref: str, *, ceiling: float) -> list[Claim]:
    """A safe target (absent across the atlas → should LICENSE) + a housekeeping control (broadly
    expressed → must NOT license, vetoed by the max leg)."""
    return [
        expression_absence_claim("absence-SAFEG", ref=ref, gene="SAFEG", ceiling=ceiling,
                                 search_cardinality=1),
        expression_absence_claim("absence-ACTB", ref=ref, gene="ACTB", ceiling=ceiling,
                                 search_cardinality=1),
    ]


def _evidence_for(claims: list[Claim]) -> dict[str, float]:
    """Per-claim absence e-value from the healthy-atlas headroom below the claim's ceiling
    (expression_absence_evalue). The ceiling is the claim's pre-registered reference leaf. Skips
    claims whose contract read fails — never fabricates."""
    out: dict[str, float] = {}
    for c in claims:
        node = _terminal_node(c)
        if node is None or not c.leaves:
            continue
        try:
            exprs = _tissue_values(node)
        except (FileNotFoundError, KeyError, ValueError):
            continue
        out[c.id] = expression_absence_evalue(exprs, ceiling=float(c.leaves[0].value))
    return out


def license_batch(
    corpus: Corpus, claims: list[Claim], *, ref: str,
    shared_cause_factors: tuple[str, ...] = ("gtex",),
) -> Corpus:
    """Confer standing on a pre-registered safety batch: run the two independent legs (max /
    high-quantile) + registry + oracle + per-claim absence e-values through run_cycle. One run_cycle
    PER CLAIM (per-claim isolation), for the same reference_leaf/select_stage-cardinality reason as
    expression_floor.license_batch — the pre-registered per-claim absence e-value is the sole
    statistical gate; the max leg's LE criterion is the hard veto. Single-cohort → REPRODUCED."""
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    try:
        dimnames_hash = load_contract(ref).dimnames_hash
    except FileNotFoundError:
        dimnames_hash = None
    factors = tuple(shared_cause_factors)
    ev_map = _evidence_for(claims)
    batch_ids = {c.id for c in claims}
    acc = corpus
    for c in claims:
        if _terminal_node(c) is None:
            continue
        solo_claims = tuple(x for x in acc.claims if x.id == c.id or x.id not in batch_ids)
        solo = acc.model_copy(update={"claims": solo_claims})
        mctx = MaterializationContext(
            id=base.id, api_version=base.api_version, data_version=base.data_version,
            dimnames_hash=dimnames_hash, shared_cause_factors=factors)
        result = run_cycle(
            solo, (ExpressionAbsenceMaxAdapter(), ExpressionAbsenceRankQAdapter()), base,
            adapter_registry=expression_absence_registry(),
            oracles=expression_absence_oracle_registry(),
            materializations={c.id: mctx},
            evidence={c.id: ev_map[c.id]} if c.id in ev_map else None,
            capability_registry=CAPABILITY_CELLS)
        updated = result.corpus.by_id().get(c.id, c)
        acc_claims = tuple(updated if x.id == c.id else x for x in acc.claims)
        acc = acc.model_copy(update={"claims": acc_claims, "fdr_ledger": result.corpus.fdr_ledger})
    return acc
