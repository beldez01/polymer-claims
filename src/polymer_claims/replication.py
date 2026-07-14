"""§2E: conceptual replication across an independent cohort.

For a claim bound to a second SE-Contract cohort (different dimnames_hash), AIR-GAP that cohort with the
same two independent methyl legs; only if BOTH legs independently satisfy the claim's criterion does the
cohort count as a replication (mirrors CapabilityCell.agreement_mode="both_satisfy_criterion" for
REGION_DELTA_BETA_CELL — the two legs are genuinely different estimators (mean-difference vs
Hodges–Lehmann) that need not be numerically close). Returns the extra (cohort-B) Satisfaction to append
to the claim's Licensing and the PRODUCT e-value e1*e2 (valid: independent data -> independent e-values
for the shared null). The grammar/protocol stay ignorant of cohort B — verify receives a finished
`replications=` map, mirroring CES-3 `materializations=` / Phase-2.1 `evidence=`. Umbrella/impure; numpy
only via methyl_adapters.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from polymer_grammar import (
    DataHandle,
    MaterializationContext,
    Satisfaction,
    SatisfactionVerdict,
    cohorts_error_independent,
)
from polymer_protocol.corpus import Corpus

from .claim_detail import _compare
from .contracts import load_contract
from .evidence import _terminal_node, betting_evalue, evidence_map
from .independence_claim import independence_verdict_for, multiply_allowed
from .methyl_adapters import (
    RegionHodgesLehmannAdapter,
    RegionMeanDiffAdapter,
    _IMPL,
    _region_group_means,
)


@dataclass(frozen=True)
class ReplicationInputs:
    """The umbrella-computed inputs to thread into run_cycle for §2E replication."""

    replications: dict[str, tuple[Satisfaction, ...]] = field(default_factory=dict)
    evidence: dict[str, float] = field(default_factory=dict)


def _rebind(node, ref_b: str):
    """Same terminal node, pointed at cohort B's DataHandle."""
    new_inputs = tuple(DataHandle(ref=ref_b) if isinstance(i, DataHandle) else i for i in node.inputs)
    return node.model_copy(update={"inputs": new_inputs})


def build_replication_inputs(
    corpus: Corpus,
    base_ctx: MaterializationContext,
    *,
    bindings: dict[str, str],
) -> ReplicationInputs:
    """For each claim id in `bindings` mapped to a cohort-B ref: air-gap cohort B and, if BOTH legs
    independently satisfy the claim's criterion and B's dimnames_hash differs from the primary
    cohort's, emit the cohort-B Satisfaction + the product e-value e1*e2. Claims with no binding
    keep their single-cohort e-value (evidence_map). Impure (reads contracts)."""
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
        handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
        if handle is None:
            continue
        try:
            contract_a = load_contract(handle.ref)
            dimnames_a = contract_a.dimnames_hash
            contract_b = load_contract(ref_b)
        except FileNotFoundError:
            continue
        if contract_b.dimnames_hash == dimnames_a:
            continue  # same cohort -> not a replication

        node_b = _rebind(node, ref_b)
        try:
            a2, b2 = _region_group_means(node_b)
            v_meandiff = RegionMeanDiffAdapter().execute(node_b, (), base_ctx).value
            v_hl = RegionHodgesLehmannAdapter().execute(node_b, (), base_ctx).value
        except (FileNotFoundError, KeyError, ValueError):
            continue

        crit = claim.evaluation_plan.criterion
        if crit.threshold is None:
            continue
        if not (
            _compare(v_meandiff, crit.comparator, crit.threshold, None)
            and _compare(v_hl, crit.comparator, crit.threshold, None)
        ):
            continue  # cohort B did not air-gap: not both legs independently show the effect

        if cid not in evidence:
            continue  # no cohort-A e-value -> cannot earn REPLICATED from cohort B alone

        e2 = betting_evalue(a2, b2, threshold=crit.threshold, comparator=crit.comparator)
        sat_b = Satisfaction(
            verdict=SatisfactionVerdict.SATISFIED,
            materialization=MaterializationContext(
                id=f"{base_ctx.id}-repl-{contract_b.contract_uid}",
                api_version=base_ctx.api_version,
                data_version=base_ctx.data_version,
                dimnames_hash=contract_b.dimnames_hash,
                shared_cause_factors=contract_b.shared_cause_factors,
            ),
        )
        replications[cid] = (sat_b,)
        # §E: only multiply the cohorts' e-values when their errors are independent (low shared-cause
        # overlap). cohorts_error_independent is None when factors are absent -> multiply as today
        # (byte-identical); False (high overlap) -> keep the single e1 so the evidence matches the
        # REPRODUCED tier independence_tier_of will stamp.
        sat_a = Satisfaction(
            verdict=SatisfactionVerdict.SATISFIED,
            materialization=MaterializationContext(
                id=f"{base_ctx.id}-primary-{contract_a.contract_uid}",
                api_version=base_ctx.api_version,
                data_version=base_ctx.data_version,
                dimnames_hash=contract_a.dimnames_hash,
                shared_cause_factors=contract_a.shared_cause_factors,
            ),
        )
        # neg-whisper ②b: the multiply is capped by BOTH the shared-cause-factor gate AND any
        # licensed/refuted `independence` CLAIM in the corpus for this cohort pair. No such claim
        # (today's corpora) -> verdict None -> multiply_allowed(v, None) == (v is not False) -> byte-identical.
        if multiply_allowed(
            cohorts_error_independent((sat_a, sat_b)),
            independence_verdict_for(
                corpus.claims, contract_a.contract_uid, contract_b.contract_uid
            ),
        ):
            evidence[cid] = evidence[cid] * e2

    return ReplicationInputs(replications=replications, evidence=evidence)
