# SELECT #3b — quality-diversity, heterodox lane, surprise-Goodhart, accumulating belief

> **Status:** design spec, approved 2026-06-03. Scope = **#3b** (all four hardening features on top
> of the #3a pursuit engine). Builds on `select.py`/`belief.py` from #3a (merge `03ae863`) and uses
> #4a's `provenance.agent_id` operator trace (merge `5d7899f`). Keystone source:
> `~/Desktop/Research/topics/epistemic-claim-foundations/generative-protocol/_FINAL_knowledge_generation_protocol.md`
> Stage 3 SELECT + §"How it gets better" (per-operator credit) + D3 (tail-coverage).

## 1. Purpose

#3a's SELECT ranks candidates on `(EIG, stakes)` under a structured cost and a budget. #3b hardens
it against **monoculture and reward-hacking** with four features:

1. **Quality-diversity (QD) portfolio** — spread the budget across structural *cells* so SELECT can't
   pile everything into one niche.
2. **Heterodox / protected-minority reserve lane** — a reserved budget fraction for *dominated*
   (off-Pareto) candidates, so contrarian claims still get pursued (anti-inbreeding floor).
3. **Surprise-Goodhart guard** — discount an *operator's* EIG by its realized grounding track record,
   so a proposer whose "surprise" systematically fails to ground is down-weighted (proper-scoring
   penalty on the proposer, not the claim).
4. **Persisted cross-cycle accumulating belief** — the #3a Beta posterior is recomputed fresh from
   `StrengthVector` each cycle; #3b makes it *accumulate* outcomes across cycles.

**Load-bearing architecture decision:** the new cross-cycle state (features 3–4) lives in a
**threaded `SelectionLedger`**, NOT in `Corpus`. `Corpus` stays "grammar IR only, 4 collections"
(claims/defeat_edges/equivalences/fdr_ledger). The ledger is *protocol pursuit-state*, not grammar
knowledge — it is passed into `run_cycle` and returned on `CycleResult`, the same way the caller
already threads `result.corpus` back in. **Zero grammar changes.** Spine invariants preserved: pure /
deterministic, one-way isolation, `Corpus` at 4 collections, no LLM / no embeddings.

## 2. The `SelectionLedger` (`ledger.py`)

A frozen protocol-side bundle of two keyed tuples (content-addressed, deterministic):

```
class ClaimOutcome(_Model):
    claim_id: str
    successes: int = Field(default=0, ge=0)   # times this claim's execution LICENSED
    failures: int = Field(default=0, ge=0)    # times REJECTED

class OperatorCredit(_Model):
    operator_id: str
    n_high_eig: int = Field(default=0, ge=0)  # selected high-EIG claims from this operator, executed
    n_grounded: int = Field(default=0, ge=0)  # ... of which LICENSED

class SelectionLedger(_Model):
    outcomes: tuple[ClaimOutcome, ...] = ()
    credits: tuple[OperatorCredit, ...] = ()
    # validators: unique claim_id in outcomes, unique operator_id in credits
    def outcome(self, claim_id) -> ClaimOutcome | None        # dict lookup
    def credit(self, operator_id) -> OperatorCredit | None
```

`SelectionLedger()` (empty) is the default — a fresh run. The caller threads `result.ledger` into the
next `run_cycle`.

## 3. Feature 4 — accumulating belief (`belief.py`)

`accumulated_belief(claim, ledger) -> Beta`:
- start from the #3a prior `prior_belief(claim)` → `Beta(α₀, β₀)`;
- look up `ledger.outcome(claim.id)`; if present, return `Beta(α₀ + successes, β₀ + failures)`;
- absent ⇒ return the #3a prior unchanged (exact back-compat for fresh claims).

**Concentration guard on `expected_information_gain` (closes the #3a follow-up).** As `α+β` grows
from accumulation, the fixed-node quadrature degrades (the #4a review's flagged failure: it can
return a spuriously high value for a sharply peaked Beta). Fix: a **settled-belief short-circuit** —
when `α + β ≥ SETTLED_CONCENTRATION` (v1 = `200.0`), `expected_information_gain` returns **0.0**
directly. This is analytically correct (a peaked belief yields negligible expected information) AND
sidesteps the quadrature regime where it misbehaves. Below the threshold, the #3a quadrature is
unchanged. (`SETTLED_CONCENTRATION` is well above the #3a prior's `KAPPA_MAX = 20`, so single-cycle
behavior is untouched.)

## 4. Feature 3 — surprise-Goodhart guard

**Operator id of a claim:** `provenance.agent_id` when `generated_by == AGENT_GENERATED` (the #4a
trace); otherwise a neutral bucket `"exogenous"` (IMPORTED/HUMAN_AUTHORED/None). Pure helper
`operator_of(claim) -> str`.

**Credit factor:** an **optimistic** smoothed grounding rate from the ledger —
`credit_factor(ledger, operator_id) = (n_grounded + CREDIT_A0) / (n_high_eig + CREDIT_A0)` with
`CREDIT_A0 = 1.0`. An **untracked operator → 1.0** (trusted until proven otherwise — this is what
makes the empty ledger an *exact* #3a no-op); a perfect track record → ~1.0; a systematically-failing
one → toward 0 as failures accumulate. Bounded `(0, 1]`.

**Discount applies to fill-order value-density, NOT to the EIG axis.** The value vector keeps the
**raw belief-EIG** (so the Pareto front is undistorted — a high-information claim stays on the front
regardless of its operator — and the high-EIG measurement, §4 update, reads a clean signal). The
operator credit instead scales the *fill-order priority*: `density = (w_e·eig + w_s·stakes)/cost ×
credit_factor(operator)`. So a distrusted operator's claims are pursued *later* (lower priority within
the budget), not removed from contention or down-graded in belief. `stakes` and the posterior are
untouched. **An empty ledger ⇒ credit 1.0 for all ⇒ density identical to #3a** (exact back-compat).

**Ledger update (post-VERIFY).** `update_ledger(ledger, executed, selection) -> SelectionLedger`:
- `executed` = the per-claim realized outcome this cycle `(claim_id, operator_id, was_high_eig,
  licensed: bool)` — derived in `run_cycle` from the verify result + the `SelectionRecord` (which
  carries each decision's EIG and whether it was selected).
- For each executed claim: bump its `ClaimOutcome` (`successes += licensed`, `failures += not
  licensed`).
- For each executed claim that was **high-EIG** when selected (`decision.value.eig ≥ HIGH_EIG`, v1 =
  `0.5` — `decision.value.eig` is the *raw* belief-EIG, since the discount is on density not the axis):
  bump its operator's `OperatorCredit` (`n_high_eig += 1`, `n_grounded += licensed`).
- Pure `(ledger, …) → ledger`; merges into existing entries by id; deterministic ordering (sorted).

## 5. Features 1–2 — QD portfolio + heterodox reserve lane (`select.py`)

**Cell key (QD niche).** `cell_of(claim) -> str` = `f"{claim.pattern.id}|{claim.subject.kind if
claim.subject else 'none'}"`. Deterministic, structural, no embeddings.

**Selection flow (replaces #3a's single greedy fill):**
1. Score each candidate → `ValueVector(eig, stakes)` where `eig` is the **raw accumulated-belief
   EIG** (undiscounted), plus `cost`, `cell`, and the operator `credit_factor`. The **fill-order
   density** is `(w_e·eig + w_s·stakes)/cost × credit_factor` (§4).
2. Compute the non-dominated **Pareto front** over `(eig, stakes)` (as #3a — undistorted by credit).
3. **Main lane** — budget `main_budget = budget × (1 − RESERVE_FRACTION)` (v1 `RESERVE_FRACTION =
   0.2`). Greedy by the credit-scaled value-density (front first, then dominated — as #3a), BUT skip a candidate whose
   **cell has hit its cap**: a cell may consume at most `CELL_CAP_FRACTION × main_budget` (v1 =
   `0.5`). A skipped-for-cell-cap candidate is passed over, the fill continues with the next cell's
   best — spreading the budget across niches.
4. **Reserve lane** — the remaining `budget × RESERVE_FRACTION`, filled greedily by value-density
   over the **dominated** candidates the main lane did not select (the heterodox/contrarian pool) —
   the anti-inbreeding floor. Cell caps do not apply in the reserve lane (it is small by
   construction).
5. Stamp `search_cardinality` (= candidate-pool size, as #3a) + record `cell` on each
   `SelectionDecision`.

`budget = None` (unbounded) ⇒ both lanes admit everything feasible; cell caps are no-ops (no budget
pressure) — degenerates to #3a's "advance the whole front," preserving back-compat.

## 6. `SelectionDecision` / `SelectionRecord` (`corpus.py`)

- `SelectionDecision` gains `cell: str = ""` and `lane: str = "main"` (`"main"` | `"reserve"`).
- `SelectionRecord` unchanged in shape; `cardinality` semantics unchanged.
- `CycleResult` gains `ledger: SelectionLedger = SelectionLedger()` (the threaded-out ledger).

## 7. `run_cycle` signature

```
run_cycle(
    corpus, adapters, ctx, oracles=None, *,
    cost_model=None, budget=None, value_weights=..., cost_weights=...,   # #3a
    proposers=(), injected=(), generation_cap=None,                       # #4a
    ledger: SelectionLedger | None = None,                                # #3b cross-cycle state
    reserve_fraction: float = 0.2,
    cell_cap_fraction: float = 0.5,
) -> CycleResult   # now also carries `ledger: SelectionLedger`
```

`ledger=None` ⇒ a fresh empty `SelectionLedger()`. With an empty ledger + default fractions, SELECT
reproduces #3a behavior **exactly**: `accumulated_belief` = the #3a prior (no outcomes), and
`credit_factor` = **1.0** for every operator (optimistic untracked default), so the fill-order density
equals #3a's `(w_e·eig + w_s·stakes)/cost` unchanged. QD cell-caps and the reserve lane only *bind*
under budget pressure with multiple cells / dominated candidates; with `budget=None` or a single cell
they are no-ops. The existing #1/#2/#3a/#4a suite must stay green (verified in testing).

**Wiring:** SELECT reads `ledger`; after `verify_stage`, `run_cycle` computes the per-claim
`executed` outcomes and calls `update_ledger`; the updated ledger rides out on `CycleResult`.

## 8. Files

All protocol-side; **no grammar changes**.

| File | New/Modify | Responsibility |
|---|---|---|
| `protocol/src/polymer_protocol/ledger.py` | new | `ClaimOutcome`, `OperatorCredit`, `SelectionLedger`, `operator_of`, `credit_factor`, `update_ledger` |
| `protocol/src/polymer_protocol/belief.py` | modify | `accumulated_belief(claim, ledger)`; `SETTLED_CONCENTRATION` short-circuit in `expected_information_gain` |
| `protocol/src/polymer_protocol/select.py` | modify | `cell_of`; operator-discounted EIG via accumulated belief; main-lane cell caps + reserve lane; `cell`/`lane` on decisions; takes `ledger` + fractions |
| `protocol/src/polymer_protocol/corpus.py` | modify | `cell`/`lane` on `SelectionDecision`; `ledger` on `CycleResult` |
| `protocol/src/polymer_protocol/cycle.py` | modify | thread `ledger`/fractions into `select_stage`; `update_ledger` after verify; return `ledger` |
| `protocol/src/polymer_protocol/__init__.py` | modify | export new public symbols |

## 9. Determinism & purity

- `SelectionLedger` is a frozen threaded value; `update_ledger` is a pure `(ledger, …) → ledger`
  merge with sorted output. No I/O, clock, randomness.
- `cell_of` / `operator_of` / `credit_factor` / `accumulated_belief` are pure deterministic functions.
- Selection stays deterministic: stable sorts with `claim_id` tie-break; cell caps and the reserve
  lane are deterministic passes over the ordered candidates.
- `Corpus` stays at exactly 4 collections; the ledger is threaded protocol state, not corpus content.

## 10. Testing

**`ledger.py`** — `operator_of` (AGENT_GENERATED→agent_id; else `"exogenous"`); `credit_factor`
(untracked→**1.0**; all-grounded→1.0; all-failed→toward 0 as failures grow; bounded `(0,1]`);
`update_ledger` bumps outcomes + credits correctly, merges by id, deterministic; validators reject
duplicate ids.

**`belief.py`** — `accumulated_belief` = prior for a fresh claim; shifts by accumulated
successes/failures; `expected_information_gain` returns 0.0 at `α+β ≥ SETTLED_CONCENTRATION` and is
unchanged below it.

**`select.py`** — `cell_of` deterministic; operator-discount lowers a failing operator's EIG;
**QD:** a corpus of many candidates in one fat cell + a few in another spreads the budget (the fat
cell can't exceed its cap while another cell has feasible candidates); **heterodox:** a dominated
candidate the main lane rejects IS admitted in the reserve lane; `cell`/`lane` recorded; `budget=None`
⇒ everything feasible (caps no-op).

**`cycle.py`** — **multi-cycle surprise-Goodhart:** an operator whose high-EIG selected claims get
REJECTED has its EIG down-weighted on the next cycle (assert a selection/ranking change across two
cycles via the threaded ledger). **accumulating belief:** a claim re-executed across cycles shifts its
Beta. `ledger=None` + defaults reproduce #3a (full #1/#2/#3a/#4a suite green). `CycleResult.ledger`
populated and threadable.

**Isolation** — the one-way guard still passes; no new grammar import of protocol.

## 11. Constants (v1 defaults, all named)

`SETTLED_CONCENTRATION = 200.0`, `CREDIT_A0 = 1.0` (optimistic smoothing — untracked operator credit
= 1.0), `HIGH_EIG = 0.5`, `RESERVE_FRACTION = 0.2`, `CELL_CAP_FRACTION = 0.5`. All module-level named
constants — no magic literals in function bodies.

## 12. Scope boundary

**#3b (this spec):** all four features — QD portfolio, heterodox reserve lane, surprise-Goodhart
operator discount, accumulating belief — on a threaded `SelectionLedger`.

**Deferred:** the embedding-based **science-novelty** niche axis (needs an embedding substrate that
doesn't exist); per-operator **budget-share throttling** beyond the EIG discount (couples to the #5
daemons' loop-economics + the calibration-against-exogenous-benchmark idea); the **EXPLORATORY
serendipity pool**; D3 **tail-coverage** entropy metric (a daemon concern, #5).
