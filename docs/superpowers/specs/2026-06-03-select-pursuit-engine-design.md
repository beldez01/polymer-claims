# SELECT — the pursuit / value engine (protocol sub-project #3a)

> **Status:** design spec, approved 2026-06-03. Scope = **#3a** (the structural core +
> minimal posterior → real EIG). The portfolio/heterodox/cross-cycle layer is a separate
> later slice (**#3b**, see §10). Pre-brainstorm primer: `2026-06-03-select-scoping-notes.md`.
> Keystone design source: `~/Desktop/Research/topics/epistemic-claim-foundations/generative-protocol/_FINAL_knowledge_generation_protocol.md` Stage 3 — SELECT.

## 1. Purpose

Today `run_cycle` runs a **dumb driver**: `execute_ground` runs *every* committed, non-gated
PENDING claim. SELECT replaces that with a **value-ranked, budget-limited selector** — the
"valve on RAM-bound, oracle-bound execution." It decides **which** frontier candidates get
committed and executed this cycle, ranked on a **two-axis value vector `(EIG, stakes)` under a
structured cost**, records the **search cardinality** that prices the implicit
multiple-comparison sweep, and lets VERIFY's significance bar **tighten as cardinality grows**
(a loose end #1 explicitly left open).

**Load-bearing scope decision:** #3a touches **zero grammar**. Everything rides on IR the
grammar already has — `StrengthVector`, `provenance.search_cardinality` (Phase 7), and the
defeat/entails graph (`entails_closure`, `grounded_extension`, defeat edges). The new code is
entirely protocol-side. This is the cleanest possible reading of "minimal."

**Spine invariants preserved:** pure / deterministic, one-way isolation (`protocol` → `grammar`
only; never `v1.2/formalclaim`), `Corpus` stays at exactly 4 collections, no LLM / no
embeddings / no external infra in the core.

## 2. Where it plugs into the spine

Keystone order: `… → SAFETY → CANONICALIZE → SELECT → COMMIT → EXECUTE → VERIFY → INTEGRATE`.

Current `run_cycle` chain:

```
represent → canonicalize → safety_gate → commit → execute_ground → verify_stage → integrate
```

becomes:

```
represent → canonicalize → safety_gate → select_stage → commit → execute_ground → verify_stage → integrate
```

`select_stage` runs **right before `commit`**. `commit` / `execute_ground` then act **only on
the selected set**. Unselected claims remain in `corpus.claims` as PENDING and reappear on a
later cycle's frontier. `select_stage` is a pure `Corpus → (Corpus, SelectionRecord)` transform
like every other stage.

## 3. The value model

Each frontier candidate is scored on a **two-axis value vector `ValueVector(eig, stakes)`** and
selected under a **structured cost** within a **budget**.

### 3.1 The minimal posterior (`belief.py`)

A frozen `Beta(alpha, beta)` credence that a claim will license, derived **deterministically**
from its `StrengthVector`:

- prior mean `mu = evidence_against_null`
- concentration `kappa = KAPPA_MIN + (KAPPA_MAX - KAPPA_MIN) * (1 - uncertainty)`
  (more confident ⇒ more concentrated; v1 defaults `KAPPA_MIN = 2.0`, `KAPPA_MAX = 20.0`, tunable
  like #2's tier ceilings)
- `alpha = mu * kappa`, `beta = (1 - mu) * kappa`

**`claim.strength is None`** (an unexecuted conjecture with no prior evidence) **→ `Beta(1, 1)`**
— the honest "know-nothing" uniform prior, which correctly yields *maximum* EIG (running an
unknown claim is maximally informative).

Guards: `mu` clamped to `[0, 1]`; `alpha, beta ≥ EPS` (a small floor, e.g. `1e-6`) so the Beta
is always proper. `Beta` is a frozen `_Model` with `alpha, beta` floats.

### 3.2 EIG — the real expected-information-gain

The EXECUTE outcome is a Bernoulli trial `Y` (licenses = 1 / not = 0). EIG is the **mutual
information `I(Y; theta)`** between that outcome and the Beta credence `theta` — the textbook
expected reduction in uncertainty about `theta` from observing one outcome:

```
EIG = I(Y; theta) = H_b(mu) - E_theta[ H_b(theta) ]
```

where `H_b` is binary entropy in **bits** (`-p·log2 p - (1-p)·log2(1-p)`, with `0·log0 = 0`),
`mu = alpha / (alpha + beta)` is the predictive `P(Y=1)`, and `E_theta[H_b(theta)]` is the
expectation of binary entropy under `Beta(alpha, beta)`.

`E_theta[H_b(theta)]` is computed by a **fixed-node deterministic quadrature** over `[0,1]`
(a fixed `N`-node grid, `N = 64` v1) of `H_b(t) · pdf_Beta(t; alpha, beta)`, where the Beta pdf
uses `math.lgamma` (stdlib only — no `digamma`, no `scipy`). Same nodes every call ⇒
byte-reproducible. EIG is bounded in `[0, 1]` bits.

Properties to assert in tests: `Beta(1,1)` (uniform) yields the **maximum** EIG; a sharply
concentrated Beta (large `kappa`, `mu` near 0 or 1) yields EIG near 0; EIG ≥ 0 always.

### 3.3 Stakes — purely structural (`stakes.py`)

The size of a claim's **forward dependency cone**: how many claims would need re-evaluation if
this claim's grounded status flipped. Computed from the grammar's `entails_closure` plus the
defeat edges in `corpus.defeat_edges`:

```
dependency_cone(corpus, claim_id) -> frozenset[claim_id]
    # claims reachable from claim_id via entailment edges + claims it attacks (defeat edges),
    # transitively; excludes claim_id itself.

stakes(corpus, claim_id) -> float
    # |dependency_cone|, with LICENSED dependents weighted by LICENSED_STAKE_WEIGHT (v1 = 2.0);
    # an honest weighted count, no hidden scalarization of the strength vector.
```

Empty cone ⇒ stakes 0. This is fully deterministic and uses only existing grammar graph
functions.

### 3.4 Cost (`cost.py`)

Cost is a **passed-in protocol config** (like `OracleRegistry` / `adapters`), never grammar IR:

```
class CostVector(_Model):       # frozen
    wall_latency: float = 0.0
    capital: float = 0.0
    human_hours: float = 0.0
    failure_rate: float = 0.0   # in [0,1]
    oracle_queue_depth: float = 0.0

class CostModel(_Model):        # frozen; passed into run_cycle
    costs: tuple[tuple[str, CostVector], ...] = ()   # (claim_id, CostVector)
    default: CostVector = CostVector()
    def resolve(self, claim_id) -> CostVector        # default for unlisted ids

def aggregate_cost(vec: CostVector, weights: CostWeights) -> float
    # weighted sum → a single positive scalar budget-consumer; weights passed-in config.
    # Clamped to >= COST_FLOOR (e.g. 1e-6) so value-density never divides by zero.
```

`oracle_queue_depth` is the natural seat for #2's `OracleRegistry` to later supply per-oracle
queue pressure; for #3a it is just another cost component the caller sets.

### 3.5 Selection under cost (`select.py`)

`ValueVector(eig, stakes)` is a genuine Pareto vector — reuse the `dominates` pattern
(componentwise ≥ with at least one strict). Selection:

1. Score every candidate → `(ValueVector, cost_scalar)`.
2. Compute the **non-dominated value front**.
3. **Fill the budget greedily** by an *explicit, configurable* value-density
   `(w_e·eig + w_s·stakes) / cost_scalar` (`ValueWeights` passed-in). The scalarization lives
   **only in the fill order**, never in the value definition — you cannot knapsack a partial
   order without *some* total order, so we make it external and explicit.
4. Front members are admitted before dominated candidates; dominated candidates are admitted
   only if budget remains.
5. Ties broken by `claim_id` (lexicographic) for determinism.
6. Unselected candidates stay PENDING (untouched in `corpus.claims`).

`budget = None` ⇒ **unbounded**: the whole feasible set is selected, degenerating to the old
driver's behavior (preserves existing callers/tests).

`SelectionRecord` (protocol-side, returned in the cycle result — **not** stored in `Corpus`):

```
class SelectionDecision(_Model):
    claim_id: str
    selected: bool
    value: ValueVector
    cost: float
    rank: int            # fill order among candidates (0 = first admitted)

class SelectionRecord(_Model):
    decisions: tuple[SelectionDecision, ...] = ()
    cardinality: int = 0   # size of the candidate pool ranked this cycle
```

## 4. Search cardinality

On each **selected** claim, `select_stage` writes
`provenance.search_cardinality = <size of the candidate pool it ranked this cycle>` — the
multiple-comparison count — via the same `_with_*` round-trip pattern `verify_stage` uses
(`Claim.model_validate(claim.model_copy(update=...).model_dump())`). The field already exists
in the grammar (Phase 7); SELECT is the stage that *sets it meaningfully*. (Per-QD-cell
cardinality is a #3b refinement.)

## 5. The cardinality-scaled VERIFY bar (closes #1's deferral)

`verify_stage` already records that cardinality is *present*; now it *uses* it. We treat
`(1 - evidence_against_null)` as a **pseudo-p-value** `p` and apply a **Benjamini–Hochberg
threshold** whose multiple-comparison denominator is the recorded **search cardinality `M`**
(the full candidate pool that was screened to surface this claim, from §4) — a conditional /
selective-inference analogue:

- Within a cycle, the selected claims share one candidate pool of size `M` (stamped as each
  one's `provenance.search_cardinality`). Collect the selected claims' pseudo-p-values, sort
  ascending `p_(1) ≤ … ≤ p_(s)` (`s ≤ M`).
- BH at level `Q` (v1 default `Q = 0.10`, tunable) with denominator `M`: largest `k` with
  `p_(k) ≤ (k / M)·Q`; permit licensing for all selected claims with `p ≤ p_(k)`. Using `M`
  (not `s`) charges for the *full implicit sweep*, not just the survivors.
- A claim may license **only if** it passes both the existing air-gapped two-adapter agreement
  **and** this bar.

**Load-bearing invariant: at `M = 1` the bar is the identity** — a single-candidate cycle gets
`p ≤ (1/1)·Q = Q`, which must reproduce the pre-#3 licensing behavior for every existing
single-claim test. The bar only *tightens* as `M` grows.

**Fallback rule** (if BH proves awkward to thread): a monotone per-claim threshold on the
pseudo-p-value `p ≤ Q / M` (Bonferroni — also identity at `M = 1`). Spec BH; keep Bonferroni as
the documented fallback.

**Migration caution:** auditing #1's existing tests, any cycle that incidentally executes
`m > 1` claims through `verify_stage` may now see a tightened bar. The implementer must run the
full #1 suite after wiring the bar and reconcile any failure as *either* a genuine behavior
change to accept (and update the test with a comment) *or* a sign `base`/`Q` is mis-set.
`m = 1` paths must remain byte-identical.

## 6. Files

All protocol-side; **no grammar changes**.

| File | Responsibility |
|---|---|
| `protocol/src/polymer_protocol/belief.py` | `Beta`, `prior_belief(claim)`, `expected_information_gain(beta)` |
| `protocol/src/polymer_protocol/stakes.py` | `dependency_cone(corpus, claim_id)`, `stakes(corpus, claim_id)` |
| `protocol/src/polymer_protocol/cost.py` | `CostVector`, `CostModel`, `CostWeights`, `aggregate_cost` |
| `protocol/src/polymer_protocol/select.py` | `ValueVector`, `ValueWeights`, Pareto front + budget knapsack, `select_stage`, `SelectionRecord`, `SelectionDecision` |
| `protocol/src/polymer_protocol/verify.py` (modify) | cardinality-scaled BH bar (consumes `provenance.search_cardinality`) |
| `protocol/src/polymer_protocol/cycle.py` (modify) | insert `select_stage` before `commit`; thread `cost_model` / `budget` / `value_weights` / `cost_weights`; execute only the selected set; return `SelectionRecord` in the cycle result |
| `protocol/src/polymer_protocol/__init__.py` (modify) | export the new public symbols |

## 7. `run_cycle` signature

```
run_cycle(
    corpus, adapters, ctx, *,
    oracles: OracleRegistry | None = None,         # #2, unchanged
    cost_model: CostModel | None = None,           # None ⇒ all-default cost
    budget: float | None = None,                   # None ⇒ unbounded (old behavior)
    value_weights: ValueWeights = <default>,
    cost_weights: CostWeights = <default>,
) -> CycleResult   # now also carries `selection: SelectionRecord`
```

All new params are keyword-only with defaults that reproduce pre-#3 behavior, so every existing
caller and test compiles unchanged.

## 8. Determinism & purity

- Fixed-node quadrature (same `N` nodes every call) ⇒ EIG is byte-reproducible.
- Selection: stable sort with `claim_id` lexicographic tie-break ⇒ deterministic order.
- `select_stage` is a pure `Corpus → (Corpus, SelectionRecord)` transform; no I/O, no clock, no
  randomness.
- `Corpus` stays at exactly 4 collections — `SelectionRecord` is cycle-ephemeral output, never
  persisted state.

## 9. Testing

**`belief.py`** — `prior_belief` maps strength axes to `(alpha, beta)` per the formula;
`strength None → Beta(1,1)`; EIG of `Beta(1,1)` is the maximum; EIG of a sharply concentrated
Beta ≈ 0; EIG ≥ 0; EIG bounded ≤ 1 bit; byte-identical across repeated calls.

**`stakes.py`** — empty cone ⇒ 0; a claim that entails/attacks K others ⇒ cone size K;
LICENSED dependents weighted; transitivity through `entails_closure`.

**`cost.py`** — `resolve` returns the listed `CostVector` or `default`; `aggregate_cost` is the
weighted sum, floored at `COST_FLOOR`.

**`select.py`** — empty frontier ⇒ select nothing; `budget = 0` ⇒ nothing; `budget = None` ⇒
the whole feasible set (old behavior); a dominated high-cost candidate loses to a cheaper
front member; ties broken by `claim_id`; `search_cardinality` written on selected claims equals
the pool size; `SelectionRecord` faithfully records every decision.

**`verify.py`** — `m = 1` is the identity (a previously-licensing claim still licenses); a
claim that licenses alone **fails** when selected among many weak candidates; BH monotonicity
(more candidates ⇒ bar no looser).

**`cycle.py`** — only the selected subset is executed; unselected stay PENDING and reappear
next cycle; the full #1 + #2 suites stay green (reconcile any `m > 1` interaction per §5); the
cycle result carries the `SelectionRecord`.

**Isolation** — the existing one-way guard (`protocol` imports `grammar`, never the reverse,
never `v1.2/formalclaim`) still passes; no new grammar import of protocol.

## 10. Scope boundary

**#3a (this spec):** §1–§9 — minimal posterior, real EIG, structural stakes, structured cost,
Pareto-front budget knapsack replacing the dumb driver, search-cardinality recording, the
cardinality-scaled BH VERIFY bar.

**Deferred to #3b** (a later slice, brushes #4/#5): quality-diversity cells; protected-minority
/ heterodox reserve lane; surprise-Goodhart proper-scoring guard; **persisted cross-cycle
accumulating belief** (real Bayesian updating from realized EXECUTE outcomes — a 5th piece of
state, needs cross-cycle history); per-QD-cell cardinality.

**Deferred indefinitely** (needs an embedding/benchmark substrate that doesn't exist yet):
science-novelty axis + the two-axis calibrated posterior (embeddings + external knowledge
graph); per-operator credit ledger (couples to GENERATE #4 + daemons #5); real async batch
scheduler / in-flight queue re-evaluation.

## 11. Tunable constants (v1 defaults, all named & documented)

`KAPPA_MIN = 2.0`, `KAPPA_MAX = 20.0`, `EPS = 1e-6`, quadrature `N = 64`,
`LICENSED_STAKE_WEIGHT = 2.0`, `COST_FLOOR = 1e-6`, BH `Q = 0.10`, default `ValueWeights` and
`CostWeights` (uniform v1). These mirror #2's "v1 ladder, tunable" posture — concrete defaults,
no magic numbers buried in code.
