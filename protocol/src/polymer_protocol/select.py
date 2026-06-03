"""SELECT: the pursuit/value engine — the valve replacing the dumb execute-all driver.

Scores eligible candidates on ValueVector(eig, stakes), takes the non-dominated front,
fills the budget greedily by an explicit value-density, and stamps search_cardinality on
the selected claims. Pure Corpus -> (Corpus, SelectionRecord) (spec §3.5, §4).
"""
from __future__ import annotations

from polymer_grammar import (
    Claim,
    GenerationMode,
    Provenance,
    Status,
    requires_safety_review,
)

from .base import _Model
from .belief import expected_information_gain, prior_belief
from .corpus import Corpus, SelectionDecision, SelectionRecord, ValueVector
from .cost import CostModel, CostWeights, aggregate_cost
from .stakes import stakes


class ValueWeights(_Model):
    eig: float = 1.0
    stakes: float = 1.0


def _is_candidate(claim: Claim) -> bool:
    if claim.status != Status.PENDING or claim.evaluation_plan is None:
        return False
    if claim.governance is not None and requires_safety_review(claim.governance):
        return False
    return True


def _value(corpus: Corpus, claim: Claim) -> ValueVector:
    eig = expected_information_gain(prior_belief(claim))
    return ValueVector(eig=eig, stakes=stakes(corpus, claim.id))


def _density(value: ValueVector, cost: float, w: ValueWeights) -> float:
    return (w.eig * value.eig + w.stakes * value.stakes) / cost


def _stamp_cardinality(claim: Claim, m: int) -> Claim:
    if claim.provenance is None:
        prov = Provenance(generated_by=GenerationMode.IMPORTED, search_cardinality=m)
    else:
        prov = claim.provenance.model_copy(update={"search_cardinality": m})
    return claim.model_copy(update={"provenance": prov})


def select_stage(
    corpus: Corpus,
    *,
    cost_model: CostModel,
    budget: float | None,
    value_weights: ValueWeights,
    cost_weights: CostWeights,
) -> tuple[Corpus, SelectionRecord]:
    candidates = [c for c in corpus.claims if _is_candidate(c)]
    m = len(candidates)
    if m == 0:
        return corpus, SelectionRecord()

    scored = []
    for c in candidates:
        value = _value(corpus, c)
        cost = aggregate_cost(cost_model.resolve(c.id), cost_weights)
        scored.append((c, value, cost))

    # non-dominated value front
    front_ids = set()
    for c, value, _ in scored:
        dominated = any(
            other_v.dominates(value) for oc, other_v, _ in scored if oc.id != c.id
        )
        if not dominated:
            front_ids.add(c.id)

    # fill order: front first, each group by descending value-density, ties by claim_id
    def order_key(item):
        c, value, cost = item
        return (0 if c.id in front_ids else 1, -_density(value, cost, value_weights), c.id)

    ordered = sorted(scored, key=order_key)

    selected_ids = set()
    spent = 0.0
    decisions = []
    for rank, (c, value, cost) in enumerate(ordered):
        take = budget is None or spent + cost <= budget
        if take:
            selected_ids.add(c.id)
            spent += cost
        decisions.append(
            SelectionDecision(claim_id=c.id, selected=take, value=value, cost=cost, rank=rank)
        )

    new_claims = tuple(
        _stamp_cardinality(c, m) if c.id in selected_ids else c for c in corpus.claims
    )
    record = SelectionRecord(
        decisions=tuple(sorted(decisions, key=lambda d: d.claim_id)),
        cardinality=m,
    )
    return corpus.model_copy(update={"claims": new_claims}), record
