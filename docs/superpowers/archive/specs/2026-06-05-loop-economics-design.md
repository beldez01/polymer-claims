# #5d loop-economics — design spec

> **Status:** approved design (forks self-resolved on the roadmap's recommended options — user authorized
> autonomous overnight build, 2026-06-05). The FINAL slice of sub-project #5 and of the 5-sub-project
> protocol runtime. Roadmap: `docs/superpowers/roadmaps/2026-06-04-sub5-daemons-roadmap.md` (#5d section).
> Builds on the COMPLETE spine (#1–#4b) + all 3 daemons (#5a/#5b/#5c) + the meta-tier. Rhythm: this spec →
> plan → subagent-driven build → merge no-ff → memory.

## What this builds

The **loop-economics scheduler**: a pure planner that, given the runtime state + a finite compute budget,
decides what to do next — run a full `run_cycle` pass, or one of the three daemon passes (DRIFT /
ORACLE-VALIDATION / RED-TEAM) — and returns that choice for the caller to execute. It ties the whole
runtime into one budget-governed loop: the closest thing to "the daemons run." Pure planning only — the
caller executes the recommended action and loops.

## Resolved forks (roadmap recommendations, self-approved)

- **E1 — value-ranked** (not round-robin): score each feasible action by expected value and pick the
  highest. RUN_CYCLE's value reuses the real belief-EIG machinery (#3a/#3b); the daemons' value is the size
  of the maintenance debt they'd address.
- **E2 — recommend-only** (not own-the-loop): `next_action(state, *, budget) -> ScheduledAction | None`;
  `None` means "stop" (budget exhausted or nothing worth doing). The caller executes + loops. Keeps the
  scheduler pure (no `run_until` driver owning the loop).
- **E3 — single shared budget** (not per-daemon shares): one `budget` float; each action's estimated cost
  is filtered against it; the scheduler allocates implicitly by ranking.

## The seams (already in the codebase)

- **`belief.py`**: `prior_belief(claim) -> Beta`, `accumulated_belief(claim, ledger) -> Beta`,
  `expected_information_gain(belief) -> float` (bits). The productive-work value signal.
- **`cost.py`**: `CostModel.resolve(claim_id) -> CostVector`, `aggregate_cost(vec, weights) -> float`
  (floored at `COST_FLOOR`), `CostWeights`. The cost signal.
- **`SelectionLedger`** (`ledger.py`): threaded cross-cycle pursuit state (for `accumulated_belief`).
- **The three daemon entry points** the scheduler chooses among: `run_cycle` (cycle.py), `drift_pass`
  (drift.py), `oracle_validation_pass` (oracle_validation.py), and the RED-TEAM proposer
  (`RepresentationRedTeamAdapter` via the bus). The scheduler does NOT call these — it only names which to
  run next.
- **`_gen_id`** (generate.py): to compute "is there un-red-teamed work?" (a claim `c` is red-teamable iff
  `_gen_id("rt", c.id)` is not already in the corpus and `c` is not itself a revision / a `gen-rt-*` output).
- **`MaterializationContext`** (grammar): passed in as the DRIFT feasibility/value signal.

## Component — new module `protocol/src/polymer_protocol/economics.py`

### The action vocabulary

```python
class ActionKind(str, Enum):
    RUN_CYCLE = "run_cycle"
    DRIFT = "drift"
    ORACLE_VALIDATION = "oracle_validation"
    RED_TEAM = "red_team"


# deterministic tie-break order (on a value tie, prefer the earlier kind = productive work first)
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
```

### State + config (passed-in; the scheduler reads, never mutates)

```python
class SchedulerState(_Model):
    corpus: Corpus
    ledger: SelectionLedger = SelectionLedger()
    current: MaterializationContext | None = None   # DRIFT feasibility/value (the "world now")
    probes_available: int = Field(default=0, ge=0)  # ORACLE feasibility/value (count; scheduler only ranks)
    proposers_available: bool = False               # whether GENERATE can produce this cycle
    red_team_enabled: bool = False                   # whether red-team adapters are wired (RED_TEAM gate — symmetric with current/probes_available)


class SchedulerWeights(_Model):
    cycle: float = 1.0
    drift: float = 0.01              # calibrated below the ~0.06-bit EIG-per-claim scale so productive
    oracle: float = 0.01            # work dominates by default; accumulated maintenance debt or an
    red_team: float = 0.01          # explicit weight bump still lets a daemon win
    generation_base: float = 0.1     # RUN_CYCLE value when nothing is selectable but proposers can run


class SchedulerConfig(_Model):
    weights: SchedulerWeights = SchedulerWeights()
    daemon_cost: float = Field(default=1.0, gt=0.0)       # flat estimated cost of one daemon pass
    generation_cost: float = Field(default=1.0, gt=0.0)   # RUN_CYCLE cost when generation-only
    cost_model: CostModel = CostModel()
    cost_weights: CostWeights = CostWeights()
```

The default weights make RUN_CYCLE (productive work) preferred when there is selectable work, with the
daemons (maintenance) firing when progress stalls or maintenance debt accumulates. **These are v1 tunable
heuristics** (like the oracle tier ceilings) — calibrate against real loops later.

### The scheduler

```python
def next_action(
    state: SchedulerState, *, budget: float, config: SchedulerConfig = SchedulerConfig()
) -> ScheduledAction | None:
    ...
```

Behavior (pure, deterministic):
1. Compute the candidate `(kind, feasible, value, cost)` for each `ActionKind`:
   - **RUN_CYCLE** — `sel = [c for c in corpus.claims if c.status == PENDING and c.evaluation_plan is not None]`.
     - If `sel`: `value = w.cycle * sum(expected_information_gain(accumulated_belief(c, ledger)) for c in sel)`;
       `cost = sum(aggregate_cost(cost_model.resolve(c.id), cost_weights) for c in sel)`. Feasible.
     - Elif `proposers_available`: `value = w.cycle * w.generation_base`; `cost = config.generation_cost`. Feasible.
     - Else: not feasible.
   - **DRIFT** — feasible iff `current is not None AND n_licensed > 0`; `value = w.drift * n_licensed`;
     `cost = daemon_cost`.
   - **ORACLE_VALIDATION** — feasible iff `probes_available > 0`; `value = w.oracle * probes_available`;
     `cost = daemon_cost`.
   - **RED_TEAM** — `rt = [c for c in corpus.claims if c.representation_revision is None and not
     c.id.startswith("gen-rt-") and _gen_id("rt", c.id) not in ids]`; feasible iff `state.red_team_enabled
     AND rt` (the caller-supplied gate, symmetric with DRIFT's `current` / ORACLE's `probes_available`);
     `value = w.red_team * len(rt)`; `cost = daemon_cost`.

> **Build note (2026-06-05):** the loop integration test surfaced a real runtime property — the
> cardinality-scaled BH bar (#3a) blocks licensing when ≥2 claims compete in one cycle at moderate evidence
> (pseudo-p = 1−evidence_against_null must clear `k/M·BH_Q`). The loop test therefore uses a strong-evidence
> strength (evidence_against_null≈0.99) so a multi-claim cycle still licenses. This is expected runtime
> behavior, not a scheduler bug.
2. Keep feasible candidates whose `cost <= budget` (affordable under the shared budget).
3. If none: return `None` (stop).
4. Else pick the candidate with the highest `value`; tie-break by `_KIND_ORDER` (prefer RUN_CYCLE).
   Return `ScheduledAction(kind, value, cost, rationale=<short why>)`.

Pure / deterministic: structural reads + passed-in signals only; sorted/stable selection; no clock, no
randomness, no environment read; `state` is never mutated (the scheduler recommends; the caller executes).

## Data flow — the budget-governed loop (caller pattern, NOT owned by the scheduler)

```python
state = SchedulerState(corpus=corpus, ledger=ledger, current=ctx, probes_available=len(probes),
                       proposers_available=bool(proposers))
remaining = budget
while (action := next_action(state, budget=remaining, config=cfg)) is not None:
    remaining -= action.estimated_cost
    if action.kind is ActionKind.RUN_CYCLE:
        result = run_cycle(state.corpus, adapters, ctx, proposers=proposers, ledger=state.ledger, ...)
        state = state.model_copy(update={"corpus": result.corpus, "ledger": result.ledger})
    elif action.kind is ActionKind.DRIFT:
        new_corpus, _rec = ... # caller runs drift_pass + (optionally) reopen_drifted
        state = state.model_copy(update={"corpus": new_corpus})
    elif action.kind is ActionKind.ORACLE_VALIDATION:
        new_registry, _rec = oracle_validation_pass(registry, probes=probes); ...
    elif action.kind is ActionKind.RED_TEAM:
        ... # caller runs a run_cycle with the red-team proposer
```

The scheduler is recommend-only; the caller maps each `ActionKind` to the right pass and threads the state.
A test demonstrates a short real loop (run it to completion: progress is made, the loop terminates).

## Scope fences (explicit non-goals)

- **Recommend-only** — no `run_until(budget)` driver in the package; the caller owns the loop (purity).
- **Value/cost are v1 tunable heuristics** — RUN_CYCLE reuses real belief-EIG + CostModel; daemons use
  count-scaled value + a flat per-pass cost. Not a learned/optimal policy; calibrate later.
- **The scheduler does NOT execute** any pass (it names the next action; the caller runs it).
- **No new Corpus collection** — `SchedulerState` is passed-in/threaded config, not persisted IR.
- **Grammar untouched**; protocol-only.

## Invariants preserved

- One-way isolation: `economics.py` imports `polymer_grammar` (Status, MaterializationContext) + protocol
  siblings (`.corpus`, `.belief`, `.cost`, `.ledger`, `.generate._gen_id`); grammar never imports protocol.
- All models frozen + tuples; pure/deterministic; everything time-like passed in.
- Exports: add `ActionKind`, `ScheduledAction`, `SchedulerState`, `SchedulerWeights`, `SchedulerConfig`,
  `next_action` to `protocol/__init__.py`.

## Testing

**`next_action` (`protocol/tests/test_economics.py`):**
- Empty corpus, no signals → `None` (nothing to do).
- `budget=0` (or below every action's cost) → `None` (nothing affordable).
- Only selectable PENDING+plan claims → RUN_CYCLE; `estimated_value > 0`, `estimated_cost` = aggregate over them.
- No selectable but `proposers_available=True` → RUN_CYCLE (generation base value/cost).
- Only LICENSED claims + `current` set → DRIFT feasible/chosen; without `current` → DRIFT not feasible.
- `probes_available > 0` → ORACLE_VALIDATION feasible; `= 0` → not.
- Un-red-teamed claims present → RED_TEAM feasible; once every claim has a `gen-rt-*` twin (or is a revision)
  → RED_TEAM not feasible (converges).
- **Value ranking**: with default weights and a high-EIG selectable set, RUN_CYCLE beats the daemons; bump
  `weights.drift` and DRIFT wins — pins value-ranked behavior.
- **Budget gating**: when the top-value action's cost exceeds budget but a cheaper feasible action fits, the
  cheaper one is returned; when nothing fits, `None`.
- **Determinism + purity**: same state → same `ScheduledAction`; `next_action` does not mutate `state`
  (assert `state` unchanged after the call); tie-break prefers RUN_CYCLE.

**The loop (integration):**
- Drive the caller loop over a corpus of PENDING+plan claims with a finite budget + the reference daemon
  inputs: it makes progress (≥1 claim licenses) and TERMINATES (returns `None` within the budget). Pins that
  the recommend-only loop ties the runtime together and halts.

**Package:**
- All six symbols import from `polymer_protocol`.

## Files

- Create: `protocol/src/polymer_protocol/economics.py`
- Modify: `protocol/src/polymer_protocol/__init__.py` (6 exports)
- Test:   `protocol/tests/test_economics.py`
