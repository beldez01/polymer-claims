"""SELECT: the pursuit/value engine — the valve replacing the dumb execute-all driver.

Scores eligible candidates on ValueVector(eig, stakes), takes the non-dominated front,
fills the budget greedily by an explicit value-density, and stamps search_cardinality on
the selected claims. Pure Corpus -> (Corpus, SelectionRecord) (spec §3.5, §4).

#3b adds: cross-cycle EIG from accumulated_belief, per-operator credit discount on the
fill-order density (Pareto front + EIG axis stay RAW), quality-diversity structural cells
with a per-cell budget cap, and a heterodox reserve lane for dominated candidates.
"""
from __future__ import annotations

from collections.abc import Mapping

from polymer_grammar import (
    Claim,
    DataHandle,
    GenerationMode,
    Provenance,
    Status,
    is_relation,
    requires_safety_review,
)

from .base import _Model
from .belief import accumulated_belief, expected_information_gain
from .corpus import Corpus, SelectionDecision, SelectionRecord, ValueVector
from .cost import CostModel, CostWeights, aggregate_cost
from .ledger import SelectionLedger, credit_factor, operator_of
from .stakes import stakes


class ValueWeights(_Model):
    eig: float = 1.0
    stakes: float = 1.0


def cell_of(claim: Claim) -> str:
    """A structural QD niche key: (pattern id, subject kind). No embeddings (spec §5)."""
    kind = claim.subject.kind if claim.subject is not None else "none"
    return f"{claim.pattern.id}|{kind}"


def _is_candidate(claim: Claim) -> bool:
    # Defense-in-depth (spec §9): relation meta-claims must never enter the SELECT/EXECUTE/FDR
    # lane, mechanically — not merely because today's construction leaves them CONJECTURED with
    # no plan (the PENDING+plan check below would already exclude them incidentally).
    if is_relation(claim):
        return False
    if claim.status != Status.PENDING or claim.evaluation_plan is None:
        return False
    if claim.governance is not None and requires_safety_review(claim.governance):
        return False
    return True


def _value(corpus: Corpus, claim: Claim, ledger: SelectionLedger) -> ValueVector:
    eig = expected_information_gain(accumulated_belief(claim, ledger))
    return ValueVector(eig=eig, stakes=stakes(corpus, claim.id))


def _density(value: ValueVector, cost: float, w: ValueWeights) -> float:
    return (w.eig * value.eig + w.stakes * value.stakes) / cost


# Tunable: a candidate whose plan target cohort overlaps its own prior-derivation cohorts is a
# confirmatory (weak severe) test, so its fill-order density is discounted. 1.0 == inert.
CONFIRMATORY_RANK_PENALTY: float = 0.5


def _severity_factor(claim: Claim, cohort_of_ref: Mapping[str, str]) -> float:
    """Data-blind: reads only the claim's prior_cohorts provenance and its plan's DataHandle refs
    (resolved to cohort ids via the injected map). Never executes / reads test data. 1.0 unless a
    confirmatory overlap is provable from metadata."""
    prior = claim.provenance.prior_cohorts if claim.provenance is not None else ()
    if not prior or not cohort_of_ref or claim.evaluation_plan is None:
        return 1.0
    targets = {
        cohort_of_ref[i.ref]
        for n in claim.evaluation_plan.graph.nodes
        for i in n.inputs
        if isinstance(i, DataHandle) and i.ref in cohort_of_ref
    }
    if not targets:
        return 1.0
    return CONFIRMATORY_RANK_PENALTY if (set(prior) & targets) else 1.0


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
    ledger: SelectionLedger = SelectionLedger(),
    reserve_fraction: float = 0.0,
    cell_cap_fraction: float = 1.0,
    cohort_of_ref: Mapping[str, str] | None = None,
) -> tuple[Corpus, SelectionRecord]:
    candidates = [c for c in corpus.claims if _is_candidate(c)]
    m = len(candidates)
    if m == 0:
        return corpus, SelectionRecord()

    cmap = cohort_of_ref or {}
    sev_of = {c.id: _severity_factor(c, cmap) for c in candidates}

    scored = []  # (claim, value, cost, cell, credit)
    for c in candidates:
        value = _value(corpus, c, ledger)
        cost = aggregate_cost(cost_model.resolve(c.id), cost_weights)
        cell = cell_of(c)
        credit = credit_factor(ledger, operator_of(c))
        scored.append((c, value, cost, cell, credit))

    front_ids = set()
    for c, value, _, _, _ in scored:
        dominated = any(ov.dominates(value) for oc, ov, _, _, _ in scored if oc.id != c.id)
        if not dominated:
            front_ids.add(c.id)

    def density(item) -> float:
        c, value, cost, cell, credit = item
        return _density(value, cost, value_weights) * credit * sev_of[c.id]

    def order_key(item):
        c, value, cost, cell, credit = item
        return (0 if c.id in front_ids else 1, -density(item), c.id)

    ordered = sorted(scored, key=order_key)

    if budget is None:
        main_budget = None
        reserve_budget = 0.0
    else:
        reserve_budget = budget * reserve_fraction
        main_budget = budget - reserve_budget
    cell_cap = None if main_budget is None else main_budget * cell_cap_fraction

    selected_ids: set[str] = set()
    lane_of: dict[str, str] = {}
    cell_spend: dict[str, float] = {}
    main_spent = 0.0
    for item in ordered:
        c, value, cost, cell, credit = item
        if main_budget is not None:
            if main_spent + cost > main_budget:
                continue
            if cell_cap is not None and cell_spend.get(cell, 0.0) + cost > cell_cap:
                continue
        selected_ids.add(c.id)
        lane_of[c.id] = "main"
        main_spent += cost
        cell_spend[cell] = cell_spend.get(cell, 0.0) + cost

    reserve_spent = 0.0
    for item in ordered:
        c, value, cost, cell, credit = item
        if c.id in selected_ids or c.id in front_ids:
            continue
        if reserve_spent + cost > reserve_budget:
            continue
        selected_ids.add(c.id)
        lane_of[c.id] = "reserve"
        reserve_spent += cost

    decisions = []
    for rank, item in enumerate(ordered):
        c, value, cost, cell, credit = item
        decisions.append(SelectionDecision(
            claim_id=c.id, selected=c.id in selected_ids, value=value, cost=cost,
            rank=rank, cell=cell, lane=lane_of.get(c.id, "main"),
        ))

    new_claims = tuple(
        _stamp_cardinality(c, m) if c.id in selected_ids else c for c in corpus.claims
    )
    record = SelectionRecord(
        decisions=tuple(sorted(decisions, key=lambda d: d.claim_id)),
        cardinality=m,
    )
    return corpus.model_copy(update={"claims": new_claims}), record
