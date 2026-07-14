"""§2E replication for the expression-floor spine — the expression-floor analog of replication.py
(which is methyl-only). Air-gaps a second cohort with the two independent expression-floor legs; only if
BOTH clear the claim's FLOOR (the reference_leaf QuantityLeaf value) does cohort B count, and only if the
cohorts are error-independent (disjoint shared_cause_factors) are the e-values multiplied. Umbrella/impure."""
from __future__ import annotations

from polymer_grammar import (
    DataHandle, MaterializationContext, Satisfaction, SatisfactionVerdict, cohorts_error_independent,
)
from polymer_protocol.corpus import Corpus

from .claim_detail import _compare
from .contracts import load_contract
from .evidence import _terminal_node, evidence_map
from .independence_claim import independence_verdict_for, multiply_allowed
from .expression_floor_adapters import ExpressionFloorHLAdapter, ExpressionFloorMeanAdapter
from .expression_floor_evidence import expression_floor_evalue
from .replication import ReplicationInputs, _rebind

_IMPL = "expression::floor"


def build_expr_replication_inputs(
    corpus: Corpus, base_ctx: MaterializationContext, *,
    bindings: dict[str, str], factors_a: tuple[str, ...], factors_b: tuple[str, ...],
) -> ReplicationInputs:
    """For each claim id in `bindings` mapped to a cohort-B ref: air-gap cohort B and, if BOTH legs
    independently clear the claim's floor (the reference_leaf QuantityLeaf value) and B's
    dimnames_hash differs from the primary cohort's, emit the cohort-B Satisfaction + the product
    e-value e1*e2. `evidence_map` (generic, threshold-only) has no entry for reference_leaf claims,
    so cohort A's own e-value (e1) is seeded here via `expression_floor_evalue` on the unrebound
    (cohort-A) node when missing. Claims with no binding keep their evidence_map e-value untouched.
    Impure (reads contracts)."""
    if not factors_a or not factors_b:
        raise ValueError("shared_cause_factors must be non-empty for both cohorts (else the §E gate "
                         "is inert and over-credits)")
    evidence = dict(evidence_map(corpus))
    replications: dict[str, tuple[Satisfaction, ...]] = {}
    by_id = {c.id: c for c in corpus.claims}

    for cid, ref_b in bindings.items():
        claim = by_id.get(cid)
        if claim is None:
            continue
        node = _terminal_node(claim)
        if node is None or node.impl != _IMPL:
            continue
        # Seed cohort A's own single-cohort e-value FIRST (evidence_map has no entry for reference_leaf
        # claims). Do it before the cohort-B checks so a claim whose cohort B fails to air-gap still keeps
        # its cohort-A e-value (falls back to REPRODUCED rather than losing its slot).
        if cid not in evidence:
            try:
                evidence[cid] = expression_floor_evalue(node)
            except (FileNotFoundError, KeyError, ValueError):
                continue  # no cohort-A e-value at all -> cannot license this claim
        handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
        if handle is None:
            continue
        try:
            contract_a = load_contract(handle.ref)
            contract_b = load_contract(ref_b)
        except FileNotFoundError:
            continue
        if contract_b.dimnames_hash == contract_a.dimnames_hash:
            continue  # same cohort -> not a replication

        crit = claim.evaluation_plan.criterion
        if crit.reference_leaf_index is None:
            continue
        floor = claim.leaves[crit.reference_leaf_index].value   # the QuantityLeaf floor (e.g. 13)

        node_b = _rebind(node, ref_b)
        try:
            v_mean = ExpressionFloorMeanAdapter().execute(node_b, (), base_ctx).value
            v_hl = ExpressionFloorHLAdapter().execute(node_b, (), base_ctx).value
        except (FileNotFoundError, KeyError, ValueError):
            continue
        # both legs must independently clear the FLOOR on cohort B (GE)
        if not (_compare(v_mean, crit.comparator, floor, None) and _compare(v_hl, crit.comparator, floor, None)):
            continue  # cohort B did not air-gap: not both legs independently clear the floor

        e2 = expression_floor_evalue(node_b)
        sat_b = Satisfaction(
            verdict=SatisfactionVerdict.SATISFIED,
            materialization=MaterializationContext(
                id=f"{base_ctx.id}-repl-{contract_b.contract_uid}",
                api_version=base_ctx.api_version, data_version=base_ctx.data_version,
                dimnames_hash=contract_b.dimnames_hash, shared_cause_factors=factors_b))
        replications[cid] = (sat_b,)
        # §E: only multiply the cohorts' e-values when their errors are independent (low shared-cause
        # overlap). cohorts_error_independent is None when factors are absent -> multiply as today
        # (byte-identical); False (high overlap) -> keep the single e1 so the evidence matches the
        # REPRODUCED tier independence_tier_of will stamp.
        sat_a = Satisfaction(
            verdict=SatisfactionVerdict.SATISFIED,
            materialization=MaterializationContext(
                id=f"{base_ctx.id}-primary-{contract_a.contract_uid}",
                api_version=base_ctx.api_version, data_version=base_ctx.data_version,
                dimnames_hash=contract_a.dimnames_hash, shared_cause_factors=factors_a))
        # neg-whisper ②b: cap the multiply by BOTH the shared-cause gate AND any independence CLAIM
        # for this cohort pair (None when absent -> byte-identical to the bare gate).
        if multiply_allowed(
            cohorts_error_independent((sat_a, sat_b)),
            independence_verdict_for(
                corpus.claims, contract_a.contract_uid, contract_b.contract_uid
            ),
        ):
            evidence[cid] = evidence[cid] * e2

    return ReplicationInputs(replications=replications, evidence=evidence)
