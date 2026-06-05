"""loop-economics (#5d) — the pure scheduler that ties the runtime into one budget-governed loop.

next_action value-ranks the next action (a run_cycle pass vs a DRIFT/ORACLE-VALIDATION/RED-TEAM daemon
pass) under a single shared compute budget, and RECOMMENDS it (recommend-only — the caller executes + loops;
no run_until driver). RUN_CYCLE's value reuses the real belief-EIG + CostModel; the daemons' value is the
size of the maintenance debt they address. Pure / deterministic; reads structural signals from the corpus +
passed-in availability; never mutates state. Weights/costs are v1 tunable heuristics. Imports nothing from
polymer_protocol's callers; grammar never imports protocol.
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field

from polymer_grammar import MaterializationContext, Status, is_representation_revision

from .base import _Model
from .belief import accumulated_belief, expected_information_gain
from .corpus import Corpus
from .cost import CostModel, CostWeights, aggregate_cost
from .generate import _gen_id
from .ledger import SelectionLedger


class ActionKind(str, Enum):
    RUN_CYCLE = "run_cycle"
    DRIFT = "drift"
    ORACLE_VALIDATION = "oracle_validation"
    RED_TEAM = "red_team"


_KIND_ORDER = {
    ActionKind.RUN_CYCLE: 0,
    ActionKind.DRIFT: 1,
    ActionKind.ORACLE_VALIDATION: 2,
    ActionKind.RED_TEAM: 3,
}


class ScheduledAction(_Model):
    kind: ActionKind
    estimated_value: float
    estimated_cost: float
    rationale: str


class SchedulerState(_Model):
    corpus: Corpus
    ledger: SelectionLedger = SelectionLedger()
    current: MaterializationContext | None = None
    probes_available: int = Field(default=0, ge=0)
    proposers_available: bool = False
    red_team_enabled: bool = False


class SchedulerWeights(_Model):
    cycle: float = 1.0
    drift: float = 0.01
    oracle: float = 0.01
    red_team: float = 0.01
    generation_base: float = 0.1


class SchedulerConfig(_Model):
    weights: SchedulerWeights = SchedulerWeights()
    daemon_cost: float = Field(default=1.0, gt=0.0)
    generation_cost: float = Field(default=1.0, gt=0.0)
    cost_model: CostModel = CostModel()
    cost_weights: CostWeights = CostWeights()


def _selectable(corpus: Corpus):
    return [c for c in corpus.claims
            if c.status == Status.PENDING and c.evaluation_plan is not None]


def _red_teamable(corpus: Corpus):
    ids = {c.id for c in corpus.claims}
    return [c for c in corpus.claims
            if not is_representation_revision(c)
            and not c.id.startswith("gen-rt-")
            and _gen_id("rt", c.id) not in ids]


def _candidate(kind: ActionKind, value: float, cost: float, rationale: str) -> ScheduledAction:
    return ScheduledAction(kind=kind, estimated_value=value, estimated_cost=cost, rationale=rationale)


def next_action(
    state: SchedulerState, *, budget: float, config: SchedulerConfig = SchedulerConfig()
) -> ScheduledAction | None:
    """Recommend the highest-value affordable action, or None to stop. Pure; never mutates `state`."""
    w = config.weights
    corpus = state.corpus
    candidates: list[ScheduledAction] = []

    # RUN_CYCLE — productive work (real belief-EIG + CostModel), else generation base if proposers can run.
    sel = _selectable(corpus)
    if sel:
        value = w.cycle * sum(
            expected_information_gain(accumulated_belief(c, state.ledger)) for c in sel
        )
        cost = sum(
            aggregate_cost(config.cost_model.resolve(c.id), config.cost_weights) for c in sel
        )
        candidates.append(_candidate(ActionKind.RUN_CYCLE, value, cost,
                                     f"{len(sel)} selectable claim(s)"))
    elif state.proposers_available:
        candidates.append(_candidate(ActionKind.RUN_CYCLE, w.cycle * w.generation_base,
                                     config.generation_cost, "generation only (no selectable claims)"))

    # DRIFT — maintenance debt = number of LICENSED claims, only when a current context is supplied.
    n_licensed = sum(1 for c in corpus.claims if c.status == Status.LICENSED)
    if state.current is not None and n_licensed > 0:
        candidates.append(_candidate(ActionKind.DRIFT, w.drift * n_licensed, config.daemon_cost,
                                     f"{n_licensed} licensed claim(s) to re-validate"))

    # ORACLE-VALIDATION — maintenance debt = number of probes ready to run.
    if state.probes_available > 0:
        candidates.append(_candidate(ActionKind.ORACLE_VALIDATION,
                                     w.oracle * state.probes_available, config.daemon_cost,
                                     f"{state.probes_available} probe(s) ready"))

    # RED-TEAM — maintenance debt = number of not-yet-red-teamed claims.
    rt = _red_teamable(corpus)
    if state.red_team_enabled and rt:
        candidates.append(_candidate(ActionKind.RED_TEAM, w.red_team * len(rt), config.daemon_cost,
                                     f"{len(rt)} claim(s) not yet red-teamed"))

    affordable = [c for c in candidates if c.estimated_cost <= budget]
    if not affordable:
        return None
    # highest value; tie-break by the deterministic kind order (prefer productive work).
    return max(affordable, key=lambda a: (a.estimated_value, -_KIND_ORDER[a.kind]))
