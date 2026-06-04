# Executable rivals + operator credit economy (protocol sub-project #4b, slice 2)

> **Status:** design spec, approved 2026-06-04. Scope = two coupled GENERATE enrichments that
> make the proposer bus **self-driving**: (2a) *executable-generation* — a rival of a planned
> claim gains a transplanted, direction-mirrored `evaluation_plan` so it becomes a real SELECT
> candidate, licenses or refutes on its own, and (via slice-1's provisional edge) autonomously
> defeats its source when it wins; (2b) a *credit economy* — GENERATE allocates its budget across
> operators by their `SelectionLedger` credit, throttling chronic Goodhart-failers to a recoverable
> probation slot. **Pure protocol, zero grammar changes** (mirrors #3a/#3b/#4a). Builds on #4a
> GENERATE (`5d7899f`) and #4b slice-1 provisional links (`64b8042`).

## 1. Purpose

#4a gave GENERATE a pure proposer bus; #4b slice-1 let its operators plant **provisional** rebut
edges (inert until the source licenses). But the pure operators emit **no-plan CONJECTURED** seeds,
which are never SELECT candidates, never execute, never license — so their provisional edges sit
**dormant forever** (the honest limit recorded in slice-1). The flywheel proposes but cannot turn on
its own output.

This slice closes that loop for the one operator where it is **pure and natural** — the rival — and
makes the bus **govern itself**:

- **2a (executable-generation):** a rival `R` of a claim `C` tests *the same data through the same
  computation, expecting the opposite result*. So when `C` carries an `evaluation_plan`, `R` can reuse
  it verbatim with a **direction-mirrored criterion**. `R` becomes a real candidate; running it
  adjudicates `C` vs `R`; if `R` wins, slice-1's provisional `R⊣C` activates and defeats `C` — with no
  human in the loop. The flywheel turns.
- **2b (credit economy):** the per-operator `OperatorCredit` / surprise-Goodhart signal already lives
  on the `SelectionLedger` (#3b) but only *feeds the VERIFY-side accounting*. Here it **feeds back into
  GENERATE**: operators whose high-EIG proposals keep grounding earn more of the generation budget;
  chronic failers are throttled — but to a recoverable **probation** slot, never killed.

Both are **pure, deterministic, additive, OFF-by-default** — no grammar change, `Corpus` stays at 4
collections.

## 2. Architecture

Two new pure protocol modules + edits to two existing ones. No grammar edits (the transplant reuses
existing `EvaluationPlan`/`ComputeGraph`/`SatisfactionCriterion` constructors and flips an existing
`Comparator` enum value; the credit read reuses #3b's `credit_factor`).

| File | Pkg | Change |
|---|---|---|
| `protocol/src/polymer_protocol/plan_synthesis.py` | protocol | **NEW** — pure `mirror_criterion` + `transplant_plan` |
| `protocol/src/polymer_protocol/proposers.py` | protocol | `rival_generation` emits a PENDING+plan rival when the source's plan transplants |
| `protocol/src/polymer_protocol/allocate.py` | protocol | **NEW** — pure `allocate_subcaps` (proportional + floor + probation, deterministic integer split) |
| `protocol/src/polymer_protocol/generate.py` | protocol | `generate_stage` enforces per-operator sub-caps from the ledger |
| `protocol/src/polymer_protocol/cycle.py` | protocol | thread `generation_credit_floor` knob + pass the prior-cycle ledger to `generate_stage` |

## 3. 2a — Executable-generation (rival plan transplant)

### 3.1 `plan_synthesis.py` (new, pure)

```python
from polymer_grammar import Comparator, EvaluationPlan, SatisfactionCriterion

_MIRROR: dict[Comparator, Comparator] = {
    Comparator.LT: Comparator.GE,
    Comparator.GE: Comparator.LT,
    Comparator.LE: Comparator.GT,
    Comparator.GT: Comparator.LE,
    Comparator.EQ: Comparator.NE,
    Comparator.NE: Comparator.EQ,
    # WITHIN_TOL: no single-comparator complement -> not mirrorable (returns None)
}


def mirror_criterion(criterion: SatisfactionCriterion) -> SatisfactionCriterion | None:
    """The logical complement of `criterion` at the SAME boundary, so on identical data
    exactly one of {criterion, mirror} is SATISFIED. None when the comparator has no
    single-Comparator complement (WITHIN_TOL)."""
    flipped = _MIRROR.get(criterion.comparator)
    if flipped is None:
        return None
    return criterion.model_copy(update={"comparator": flipped})


def transplant_plan(plan: EvaluationPlan) -> EvaluationPlan | None:
    """Reuse the source graph VERBATIM (same data + ops) with a mirrored criterion, so the
    rival co-evaluates against its source. None when the criterion can't be mirrored."""
    mirrored = mirror_criterion(plan.criterion)
    if mirrored is None:
        return None
    return plan.model_copy(update={"criterion": mirrored})
```

**Why reuse the graph verbatim:** the graph computes the *statistic* (e.g. an effect estimate) on the
data; the *criterion* is what turns that statistic into a SATISFIED/REFUTED verdict for a given
direction. The rival makes the opposite directional claim about the same statistic, so it shares the
graph and only flips the criterion. The mirror is the criterion's logical complement **at the same
boundary** (same `threshold`/`reference_leaf_index`), guaranteeing that on one data realization exactly
one of `{C, R}` satisfies — they are a genuine adjudicator pair.

**`model_copy(update=...)` caveat:** it bypasses validators, but here the flipped comparator is never
`WITHIN_TOL` and we never add/remove `tolerance`, so the `_tolerance_iff_within_tol` and
`_exactly_one_target` invariants are preserved by construction. (A test asserts the mirrored criterion
is a valid `SatisfactionCriterion` via `model_validate(model_dump())`.)

### 3.2 `rival_generation` enrichment (`proposers.py`)

Current: every rival is `CONJECTURED`, no plan. New: when the source `C` has a transplantable plan,
the rival is **`PENDING` / `UNTESTED` carrying the transplanted plan** (a real SELECT candidate);
otherwise the existing CONJECTURED no-plan rival (unchanged fallback). The provisional `R⊣C` rebut edge
is emitted in **both** cases (unchanged from slice-1).

```python
            rid = _gen_id("rival", c.id, d.value)
            transplanted = (
                transplant_plan(c.evaluation_plan) if c.evaluation_plan is not None else None
            )
            if transplanted is not None:
                rival = Claim(
                    id=rid, title=f"rival({d.value}) of {c.id}", pattern=c.pattern, leaves=c.leaves,
                    status=Status.PENDING, pending_reason=PendingReason.UNTESTED,
                    subject=c.subject, conclusion=rival_concl,
                    evaluation_plan=transplanted, provenance=_generated_by(corpus, RIVAL_OP),
                )
            else:
                rival = Claim(
                    id=rid, title=f"rival({d.value}) of {c.id}", pattern=c.pattern, leaves=c.leaves,
                    status=Status.CONJECTURED, subject=c.subject, conclusion=rival_concl,
                    provenance=_generated_by(corpus, RIVAL_OP),
                )
            edge = DefeatEdge(source=rid, target=c.id, kind=DefeatEdgeKind.REBUT, provisional=True)
            proposals.append(Proposal(operator_id=RIVAL_OP, claim=rival, edges=(edge,)))
```

(`PendingReason` is added to the grammar import. `frontier_attack` is unchanged — its seeds have no
conclusion and no source plan, so they remain dormant; making *them* executable needs the
embedding/LLM operator and is deferred to slice-3.)

### 3.3 Belief-neutrality and the autonomous-activation path

- **At plant time, still belief-neutral.** A planned rival is `PENDING`, not `LICENSED`, so its
  provisional `R⊣C` edge is inert (slice-1 semantics) — the grounded extension of the existing claims
  is unchanged when the rival is folded in. The #4a/#4b belief-neutrality tests still hold.
- **The loop turns when `R` wins.** In the same cycle: GENERATE plants `R` (PENDING+plan) → the
  post-GENERATE scaffolding recompute (#4a) makes `R` a candidate → SELECT may pick it → EXECUTE runs
  the transplanted plan → VERIFY licenses `R` iff the data satisfied the mirrored criterion. If `R`
  licenses, INTEGRATE's `_in_set` (slice-1 Task 2 — honors provisional activation) sees `R ∈ licensed`
  → `R⊣C` is now effective → `C` is contested/defeated in the tail `represent`. If `R` refutes, `C` is
  untouched. This is exactly slice-1's end-to-end activation, now driven by a **generated** rival
  rather than a hand-injected one.
- **A licensed source cannot be overturned by its own data.** If `C` is already LICENSED, the same data
  that satisfied `C` necessarily *refutes* the mirror, so `R` refutes and `R⊣C` never activates — the
  rival only wins when the data genuinely favors the opposite direction. (Overturning a licensed claim
  needs *new* data — a future concern, not this slice.)

## 4. 2b — Operator credit economy

### 4.1 `allocate.py` (new, pure)

```python
def allocate_subcaps(
    operator_ids: tuple[str, ...],   # distinct ENDOGENOUS operators present this cycle, caller order
    cap: int,                        # global generation cap (> 0)
    ledger: SelectionLedger,
    *,
    floor: float,
) -> dict[str, int]:
    """Split `cap` into per-operator sub-caps. Below-floor operators get a guaranteed probation
    slot (=1, recoverable); the remainder is split among above-floor operators proportional to
    credit_factor via largest-remainder (deterministic). Sum of sub-caps == cap (or all probation
    slots when cap is too small). Caller order breaks every tie."""
```

Algorithm (deterministic; `credit_factor` from #3b, untracked → 1.0):

1. `cf[op] = credit_factor(ledger, op)` for each operator (in caller order).
2. `below = [op if cf[op] < floor]`, `healthy = [op if cf[op] >= floor]` (caller order preserved).
3. **Starved case** `cap <= len(operator_ids)` (not even one slot per operator): give 1 slot to the
   first `cap` operators in **caller order** (healthy and below interleaved exactly as they appear), 0
   to the rest; return. When budget can't seat everyone, caller order is the sole, deterministic
   tiebreak — probation does **not** preempt a healthy operator here.
4. **Normal case** `cap > len(operator_ids)`: every below-floor operator gets exactly its 1 probation
   slot. `remaining = cap - len(below)`.
   - If `healthy` is empty (all below floor): distribute the `remaining` extra slots across `below`
     round-robin in caller order (so probation operators share the leftover on top of their 1 each).
   - Else split `remaining` among `healthy` proportional to `cf` via **largest-remainder (Hamilton)**:
     `exact[op] = remaining * cf[op] / sum(cf[healthy])`; floor each to an int; hand the leftover
     `remaining - sum(floors)` slots to the operators with the largest fractional parts, ties broken by
     caller order. Each below-floor operator keeps its 1 probation slot.
5. Return `{op: subcap}` for every operator in `operator_ids` (healthy allocation ∪ `{op: 1}` for below).

**Untracked / new / exogenous operators:** `credit_factor` returns `1.0` for any operator with no
ledger entry, so a brand-new operator is born **healthy** (not on probation) — correct, and it makes
the first cycle (empty ledger) allocate purely proportionally to 1.0 (even split), i.e. graceful.

### 4.2 `generate_stage` wiring (`generate.py`)

`generate_stage` gains `ledger: SelectionLedger | None = None` and `credit_floor: float | None = None`.
The economy is **active iff** `ledger is not None and credit_floor is not None and cap is not None`
(all three needed: a ledger to read, a floor to gate, and a cap to split). When active:

1. Run proposers + injections exactly as today, producing `proposals` in caller order.
2. Determine the distinct **endogenous** operator ids present (every `p.operator_id` except
   `"exogenous"`), in first-appearance order.
3. `subcaps = allocate_subcaps(endo_ops, cap, ledger, floor=credit_floor)`.
4. Admit proposals in order, maintaining a per-operator admitted count. A proposal is discarded with
   reason **`"operator-cap"`** when its operator's `subcaps[op]` is exhausted. **Exogenous proposals
   are exempt** from sub-caps (the trusted validated-entry port) but still bound by the global `cap`.
   The global `cap` remains the hard ceiling for everyone.

When the economy is inactive (any of the three is `None`), behavior is **byte-identical to #4a** — flat
global cap, no per-operator accounting.

### 4.3 `cycle.py` wiring

`run_cycle` gains `generation_credit_floor: float | None = None` (kw-only) and passes
`ledger=<the run's ledger>, credit_floor=generation_credit_floor` into `generate_stage`. Because
GENERATE runs first in the cycle, the ledger it reads is **last cycle's** accumulated credit — an
operator's track record governs *this* cycle's generation budget. Default `None` ⇒ #4a behavior.
`CREDIT_FLOOR_DEFAULT = 0.5` is exported as the recommended value (a caller opts in with
`generation_credit_floor=0.5`); the knob is a float, not a bool, so enabling and configuring are one
act (mirrors #3a's `budget=`/#3b's `reserve_fraction=`).

## 5. Files & isolation

No new grammar modules; no grammar edits. `Corpus` unchanged (4 collections). Two new protocol modules
(`plan_synthesis.py`, `allocate.py`), both pure (stdlib + grammar IR only — no infra, no LLM, no
embeddings). Grammar still imports nothing from protocol; protocol→grammar one-way; neither imports
`v1.2/formalclaim`. Public surface: export `mirror_criterion`/`transplant_plan`,
`allocate_subcaps`, `CREDIT_FLOOR_DEFAULT` for callers/tests.

## 6. Testing

**`plan_synthesis.py`:**
- `mirror_criterion` flips each of the 6 mirrorable comparators correctly and returns `None` for
  `WITHIN_TOL`; the mirrored criterion preserves `threshold`/`reference_leaf_index` and round-trips
  through `model_validate(model_dump())`.
- `transplant_plan` reuses the graph object (same `content_hash`) and only swaps the criterion; returns
  `None` for a `WITHIN_TOL` plan.
- **Adjudicator property:** for a GT/threshold criterion, build a tiny terminal value on each side of
  the threshold and assert the source criterion and the mirror reach *opposite* verdicts (exactly one
  SATISFIED) — pins that mirror = logical complement at the same boundary.

**`proposers.py`:**
- a rival of a **planned** source is `PENDING`/`UNTESTED`, carries a transplanted plan (mirrored
  criterion, same graph), and still emits the provisional `R⊣C` edge.
- a rival of a **WITHIN_TOL-planned** source and a rival of a **no-plan** source both stay
  `CONJECTURED`/no-plan (+ provisional edge) — existing slice-1 rival tests still pass unchanged
  (their sources are planless).

**`allocate.py`:**
- proportional split among healthy operators (worked example: cap=10, cf 0.9/0.3 → 8/2) with
  largest-remainder determinism; sum == cap.
- a below-floor operator gets exactly its 1 probation slot, never 0; the rest goes to the healthy ones.
- all-below-floor → everyone on probation, leftover round-robined in caller order; starved
  `cap <= len(operators)` → first-`cap` operators in caller order get 1, rest 0 (probation does not
  preempt a healthy operator).
- empty ledger → all `cf` = 1.0 → even split.
- determinism: same inputs → identical dict across repeated calls.

**`generate.py`:**
- economy OFF (any of ledger/floor/cap `None`) → byte-identical admit set + `GenerationRecord` vs #4a
  (flat cap).
- economy ON → a low-credit operator's surplus proposals are discarded with reason `"operator-cap"`
  while a high-credit operator's are admitted; the counts match `allocate_subcaps`.
- exogenous/injected proposals are never discarded for `"operator-cap"` (only the global `"cap"`).

**`cycle.py` (end-to-end):**
- **autonomous adjudication:** a corpus with a planned, not-yet-licensed `C` (a conclusion whose
  direction the seeded data contradicts) + `rival_generation` as a proposer + a budget that admits and
  selects the rival → run the cycle(s) → the generated rival licenses, its provisional `R⊣C` activates,
  and `C` drops out of the grounded extension (the flywheel turned with no injection). Mirror case: when
  the data supports `C`, the rival refutes and `C` is untouched.
- **belief-neutral at plant:** with no budget to select the rival, planting the planned rival leaves
  the existing claims' grounded membership unchanged (provisional edge inert while `R` is PENDING).
- **credit governance through `run_cycle`:** with `generation_credit_floor=0.5` and a ledger in which
  one operator is below floor, that operator is throttled to its probation slot for the cycle; a
  follow-up cycle in which it grounds a high-EIG claim raises its credit back above the floor
  (self-healing — no absorbing death-state).

**Isolation:** `test_isolation.py` still green (grammar↔protocol one-way; no formalclaim import).

## 7. Scope boundary

**This slice (2a + 2b):** executable rivals (plan transplant + mirrored criterion) + the credit
economy (proportional + floor + probation allocation) wired through `run_cycle`.

**Deferred (slice-3 / later):** the **intelligent-operator seam** — embedding/LLM proposers as injected
adapters behind the bus (the only purity-boundary piece); making **frontier_attack seeds** executable
(needs hypothesis synthesis, not a transplant); overturning an already-LICENSED claim with *new* data
(rivals here only adjudicate within one data realization); per-axis credit or credit decay over time;
the #5 daemons. The honest limit shrinks from "no operator output self-activates" to "only rivals of
planned claims self-activate; frontier seeds still need slice-3."
