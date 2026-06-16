# #5d loop-economics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pure recommend-only scheduler that value-ranks the next runtime action (a `run_cycle` pass vs a DRIFT/ORACLE/RED-TEAM daemon pass) under a single shared compute budget — tying the whole runtime into one budget-governed loop.

**Architecture:** A new protocol module `economics.py` with `next_action(state, *, budget, config) -> ScheduledAction | None`. RUN_CYCLE value reuses the real belief-EIG (`belief.py`) + CostModel (`cost.py`); the daemons use count-scaled maintenance value + a flat per-pass cost. Pure planning — the caller executes the recommended action and loops. Protocol-only; grammar untouched; no new Corpus collection.

**Tech Stack:** Python 3.14, Pydantic v2 (frozen `_Model`, tuples), `uv`, pytest, ruff. Package `polymer_protocol` (in `protocol/`).

**Spec:** `docs/superpowers/specs/2026-06-05-loop-economics-design.md`

---

## File Structure

- `protocol/src/polymer_protocol/economics.py` — **create**: `ActionKind`, `ScheduledAction`, `SchedulerState`, `SchedulerWeights`, `SchedulerConfig`, `next_action`.
- `protocol/src/polymer_protocol/__init__.py` — **modify**: export the 6 symbols.
- `protocol/tests/test_economics.py` — **create**: scheduler unit tests + the loop integration test.

Conventions (established): all models subclass `_Model` (frozen, `extra="forbid"`, tuples). Reuses `belief.accumulated_belief`/`expected_information_gain`, `cost.aggregate_cost`/`CostModel`/`CostWeights`, `ledger.SelectionLedger`, `generate._gen_id`. `protocol/tests/conftest.py` provides `make_claim`, `make_plan`, `empty_ledger`/`ctx`/`adapters`. Tests import new symbols from `polymer_protocol.economics` until Task 2's package export.

---

### Task 1: Protocol — `economics.py` scheduler + tests

**Files:**
- Create: `protocol/src/polymer_protocol/economics.py`
- Test: `protocol/tests/test_economics.py`

- [ ] **Step 1: Write the failing scheduler tests**

Create `protocol/tests/test_economics.py`:

```python
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
    state = SchedulerState(corpus=_corpus(empty_ledger, c))
    action = next_action(state, budget=100.0)
    assert action is not None and action.kind is ActionKind.RED_TEAM
    # add the red-team twin -> 'a' is no longer red-teamable; a gen-rt-* claim is self-skipped
    twin = make_claim(_gen_id("rt", "a"), status=Status.CONJECTURED)
    converged = SchedulerState(corpus=_corpus(empty_ledger, c, twin))
    assert next_action(converged, budget=100.0) is None


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
        make_claim(f"c{i}", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_SV)
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
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd protocol && uv run pytest tests/test_economics.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'polymer_protocol.economics'`.

- [ ] **Step 3: Create `economics.py`**

Create `protocol/src/polymer_protocol/economics.py`:

```python
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

from polymer_grammar import MaterializationContext, Status

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


class SchedulerWeights(_Model):
    cycle: float = 1.0
    drift: float = 0.1
    oracle: float = 0.1
    red_team: float = 0.05
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
            if c.representation_revision is None
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
    if rt:
        candidates.append(_candidate(ActionKind.RED_TEAM, w.red_team * len(rt), config.daemon_cost,
                                     f"{len(rt)} claim(s) not yet red-teamed"))

    affordable = [c for c in candidates if c.estimated_cost <= budget]
    if not affordable:
        return None
    # highest value; tie-break by the deterministic kind order (prefer productive work).
    return max(affordable, key=lambda a: (a.estimated_value, -_KIND_ORDER[a.kind]))
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd protocol && uv run pytest tests/test_economics.py -q`
Expected: PASS (12 tests).

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/economics.py protocol/tests/test_economics.py
git commit -m "feat(protocol): next_action — pure budget-governed loop scheduler (#5d)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Protocol — exports + full-suite green

**Files:**
- Modify: `protocol/src/polymer_protocol/__init__.py`
- Test: `protocol/tests/test_economics.py`

- [ ] **Step 1: Write the failing export test**

Append to `protocol/tests/test_economics.py`:

```python
def test_economics_symbols_exported_from_package():
    import polymer_protocol as pp

    for name in ("ActionKind", "ScheduledAction", "SchedulerState",
                 "SchedulerWeights", "SchedulerConfig", "next_action"):
        assert hasattr(pp, name), f"missing export: {name}"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd protocol && uv run pytest tests/test_economics.py::test_economics_symbols_exported_from_package -q`
Expected: FAIL — `AttributeError: module 'polymer_protocol' has no attribute 'next_action'`.

- [ ] **Step 3: Add the imports and `__all__` entries**

In `protocol/src/polymer_protocol/__init__.py`, add an import block next to the other module imports:

```python
from .economics import (
    ActionKind,
    ScheduledAction,
    SchedulerConfig,
    SchedulerState,
    SchedulerWeights,
    next_action,
)
```

And add these to `__all__`:

```python
    "ActionKind",
    "ScheduledAction",
    "SchedulerConfig",
    "SchedulerState",
    "SchedulerWeights",
    "next_action",
```

- [ ] **Step 4: Run the export test to verify it passes**

Run: `cd protocol && uv run pytest tests/test_economics.py::test_economics_symbols_exported_from_package -q`
Expected: PASS.

- [ ] **Step 5: Run the full protocol suite + ruff + isolation**

Run: `cd protocol && uv run pytest -q && uv run ruff check src tests`
Expected: all green (existing protocol tests + 13 economics tests), ruff clean. `tests/test_isolation.py` still passes.

- [ ] **Step 6: Run the full grammar suite (confirm untouched + green)**

Run: `cd grammar && uv run pytest -q`
Expected: all green (this slice touches no grammar).

- [ ] **Step 7: Commit**

```bash
git add protocol/src/polymer_protocol/__init__.py protocol/tests/test_economics.py
git commit -m "feat(protocol): export loop-economics scheduler symbols (#5d — protocol runtime COMPLETE)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Progress Log

(Update after each task.)

- [ ] Task 1 — `economics.py` scheduler
- [ ] Task 2 — exports + full-suite green

## Self-review notes

- **Spec coverage:** `next_action` value-ranking + feasibility + budget gating + purity → Task 1; the loop integration → Task 1's `test_loop_makes_progress_and_terminates`; exports → Task 2. All spec test bullets map to a named test.
- **Reuse:** RUN_CYCLE value = `expected_information_gain(accumulated_belief(...))` (belief.py) + `aggregate_cost(cost_model.resolve(...))` (cost.py); RED-TEAM convergence via `_gen_id("rt", ...)` (generate.py). No re-implementation.
- **Fences honored:** recommend-only (no `run_until`); pure (no mutation — `test_deterministic_and_pure` asserts state unchanged); no new Corpus collection; grammar untouched.
- **Type consistency:** `next_action(state, *, budget, config=SchedulerConfig()) -> ScheduledAction | None`; `ScheduledAction(kind, estimated_value, estimated_cost, rationale)`; `SchedulerState(corpus, ledger, current, probes_available, proposers_available)` — identical across spec, plan, tests.
- **Determinism:** `max(..., key=(value, -kind_order))` is stable; structural reads sorted-independent (sums); no clock/random.
- **Export-timing:** Task 1 tests import from `polymer_protocol.economics`; package exports land in Task 2.
