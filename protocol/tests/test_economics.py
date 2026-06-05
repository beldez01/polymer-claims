from __future__ import annotations

from polymer_grammar import MaterializationContext, Status, StrengthVector

from polymer_protocol.corpus import Corpus
from polymer_protocol.economics import (
    ActionKind,
    SchedulerConfig,
    SchedulerState,
    SchedulerWeights,
    next_action,
)
from tests.conftest import make_claim, make_plan


def _corpus(empty_ledger, *claims):
    return Corpus(claims=tuple(claims), fdr_ledger=empty_ledger)


_CTX = MaterializationContext(id="now", api_version="v1", data_version="d1")
_SV = StrengthVector(magnitude=0.6, uncertainty=0.5, evidence_against_null=0.6,
                     severity=0.6, world_contact=0.6, explanatory_virtue=0.6)
_STRONG = StrengthVector(magnitude=0.9, uncertainty=0.3, evidence_against_null=0.99,
                         severity=0.9, world_contact=0.9, explanatory_virtue=0.9)


def test_empty_corpus_no_signals_returns_none(empty_ledger):
    state = SchedulerState(corpus=_corpus(empty_ledger))
    assert next_action(state, budget=100.0) is None


def test_zero_budget_returns_none(empty_ledger):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_SV)
    state = SchedulerState(corpus=_corpus(empty_ledger, c))
    assert next_action(state, budget=0.0) is None


def test_selectable_claims_pick_run_cycle(empty_ledger):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_SV)
    state = SchedulerState(corpus=_corpus(empty_ledger, c))
    action = next_action(state, budget=100.0)
    assert action is not None and action.kind is ActionKind.RUN_CYCLE
    assert action.estimated_value > 0.0
    assert action.estimated_cost > 0.0


def test_generation_only_run_cycle_when_proposers_available(empty_ledger):
    # no selectable claims, but proposers can run -> RUN_CYCLE is still feasible (generation base)
    c = make_claim("a", status=Status.CONJECTURED)
    state = SchedulerState(corpus=_corpus(empty_ledger, c), proposers_available=True)
    action = next_action(state, budget=100.0)
    assert action is not None and action.kind is ActionKind.RUN_CYCLE


def test_drift_feasible_only_with_current_and_licensed(empty_ledger):
    lic = make_claim("a", status=Status.LICENSED)
    # no current -> DRIFT not feasible, and nothing else feasible -> None
    assert next_action(SchedulerState(corpus=_corpus(empty_ledger, lic)), budget=100.0) is None
    # with current -> DRIFT feasible/chosen
    state = SchedulerState(corpus=_corpus(empty_ledger, lic), current=_CTX)
    action = next_action(state, budget=100.0)
    assert action is not None and action.kind is ActionKind.DRIFT


def test_oracle_feasible_only_with_probes(empty_ledger):
    c = make_claim("a", status=Status.CONJECTURED)
    no = SchedulerState(corpus=_corpus(empty_ledger, c))
    assert next_action(no, budget=100.0) is None
    yes = SchedulerState(corpus=_corpus(empty_ledger, c), probes_available=3)
    action = next_action(yes, budget=100.0)
    assert action is not None and action.kind is ActionKind.ORACLE_VALIDATION


def test_red_team_feasible_until_converged(empty_ledger):
    from polymer_protocol.generate import _gen_id

    c = make_claim("a", status=Status.CONJECTURED)
    state = SchedulerState(corpus=_corpus(empty_ledger, c), red_team_enabled=True)
    action = next_action(state, budget=100.0)
    assert action is not None and action.kind is ActionKind.RED_TEAM
    # add the red-team twin -> 'a' is no longer red-teamable; a gen-rt-* claim is self-skipped
    twin = make_claim(_gen_id("rt", "a"), status=Status.CONJECTURED)
    converged = SchedulerState(corpus=_corpus(empty_ledger, c, twin), red_team_enabled=True)
    assert next_action(converged, budget=100.0) is None   # no red-teamable left -> None even when enabled


def test_value_ranking_run_cycle_beats_daemons_by_default(empty_ledger):
    # selectable claim (RUN_CYCLE) + licensed claim w/ current (DRIFT). Default weights -> RUN_CYCLE wins.
    sel = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_SV)
    lic = make_claim("b", status=Status.LICENSED)
    state = SchedulerState(corpus=_corpus(empty_ledger, sel, lic), current=_CTX)
    assert next_action(state, budget=100.0).kind is ActionKind.RUN_CYCLE


def test_weights_can_flip_to_a_daemon(empty_ledger):
    sel = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_SV)
    lic = make_claim("b", status=Status.LICENSED)
    state = SchedulerState(corpus=_corpus(empty_ledger, sel, lic), current=_CTX)
    cfg = SchedulerConfig(weights=SchedulerWeights(drift=1000.0))
    assert next_action(state, budget=100.0, config=cfg).kind is ActionKind.DRIFT


def test_budget_excludes_unaffordable_picks_cheaper(empty_ledger):
    # RUN_CYCLE cost is high (expensive cost vector); DRIFT is the flat daemon_cost. With a budget that
    # only fits the daemon, DRIFT is returned even though RUN_CYCLE might score higher.
    from polymer_protocol.cost import CostModel, CostVector

    sel = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_SV)
    lic = make_claim("b", status=Status.LICENSED)
    state = SchedulerState(corpus=_corpus(empty_ledger, sel, lic), current=_CTX)
    cfg = SchedulerConfig(
        cost_model=CostModel(costs=(("a", CostVector(capital=50.0)),)),
        daemon_cost=1.0,
    )
    action = next_action(state, budget=2.0, config=cfg)  # RUN_CYCLE costs ~50 > 2; DRIFT costs 1
    assert action is not None and action.kind is ActionKind.DRIFT


def test_deterministic_and_pure(empty_ledger):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_SV)
    state = SchedulerState(corpus=_corpus(empty_ledger, c))
    a1 = next_action(state, budget=100.0)
    a2 = next_action(state, budget=100.0)
    assert a1 == a2
    # purity: the call did not mutate state
    assert state.corpus.by_id()["a"].status is Status.PENDING


def test_loop_makes_progress_and_terminates(empty_ledger, ctx, adapters):
    # the budget-governed caller loop: recommend -> execute -> thread state -> until None.
    from polymer_protocol.cycle import run_cycle

    claims = tuple(
        make_claim(f"c{i}", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_STRONG)
        for i in range(3)
    )
    state = SchedulerState(corpus=_corpus(empty_ledger, *claims))
    remaining = 1000.0
    steps = 0
    while (action := next_action(state, budget=remaining)) is not None and steps < 20:
        remaining -= action.estimated_cost
        if action.kind is ActionKind.RUN_CYCLE:
            result = run_cycle(state.corpus, adapters, ctx, ledger=state.ledger)
            state = state.model_copy(update={"corpus": result.corpus, "ledger": result.ledger})
        else:
            break  # no daemon inputs supplied in this minimal loop
        steps += 1
    licensed = [c for c in state.corpus.claims if c.status is Status.LICENSED]
    assert len(licensed) >= 1          # progress was made
    assert next_action(state, budget=remaining) is None  # terminates (no selectable left)


def test_economics_symbols_exported_from_package():
    import polymer_protocol as pp

    for name in ("ActionKind", "ScheduledAction", "SchedulerState",
                 "SchedulerWeights", "SchedulerConfig", "next_action"):
        assert hasattr(pp, name), f"missing export: {name}"
