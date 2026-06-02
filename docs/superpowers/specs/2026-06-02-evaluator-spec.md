# Phase 8 — The Evaluator (v1.3 grammar)

> Design spec. Status: **approved** (brainstorm 2026-06-02). Implements the
> unified spec's **runtime half** of the compiler/runtime split: the thing that
> *runs* a claim's evaluation logic against materialized data and **produces** the
> L2 `Satisfaction`s the static `Licensing` record consumes. Delivers load-bearing
> guarantee #1 — *no self-licensing (air-gapped, two-implementation verifier)* —
> at the grammar level (unified spec §4; build-order move #3).

## 0. Context — why this phase exists

v1.3 deliberately dropped v1.2's `operations` / untyped-`Statistic` layer / And-Or-Not-Cmp
inference tree when it moved from a *grammar of statistics* to a *grammar of science*.
A consequence: the current L2 (`licensing.py`) stores only the **result** of evaluation —
a static `Satisfaction(verdict, materialization)` — with **no representation of how a
claim is checked against data, and nothing that produces a Satisfaction**.

Phase 8 closes that gap. It (re)introduces a typed `operations` compute graph (as
*data*, not code) and the runtime that executes it against a `MaterializationContext`
to mint Satisfactions — but only through an **air-gapped, two-implementation agreement
gate**, so a claim can never license itself.

This is the gateway to the protocol runtime (the 8-stage flywheel) and unblocks the two
remaining Phase-7 §5 items: requirement #2 (oracle credibility-qualification, which binds
to an operation node — slot declared here) and, indirectly, dimensional enforcement.

## 1. Success criterion

A claim that carries an `evaluation_plan` can be executed by ≥2 independent adapter
implementations; their results are checked for agreement; and **only on agreement** is a
`Satisfaction` admissible. A single implementation — or two results from the *same*
identity — can never mint a Satisfaction. The grammar package stays **dependency-free and
infra-isolated** (no network/R/scipy imports; `test_isolation.py` stays green).

- **Sensitivity:** the compute graph is expressive enough to state how a real claim's
  inference is computed (a node DAG producing typed L0 Leaves, terminating in a predicate).
- **Specificity:** no self-licensing (distinct-identity gate), no paraphrased statistics
  (byte/typed drift surfaced), no untyped verdict (3-valued, dimension-checked).

## 2. Design principles (inherited invariants)

- All IR models subclass `_Model` (frozen, `extra="forbid"`). **Collections are tuples**
  (deep immutability + content-addressing). **No `dict`/`list` fields** — key/value
  params are `tuple[tuple[str, str], ...]`.
- New cross-cutting Claim fields land **additive/optional** (`X | None = None`) with
  back-compat preserved. No hard "required" gate (deferred to a later tightening phase).
- The runtime is a **total, pure function** — it never mutates a Claim; it returns new
  result values. Frozen IR discipline extends to the result models.
- `grammar/` must NEVER import `polymer_formalclaim` (enforced by `test_isolation.py`);
  `evaluate.py` additionally imports **no** infra (network/R/scipy).
- TDD: failing test first. `cd grammar && uv run pytest -q` + `uv run ruff check src tests`.

## 3. The operations IR — `operations.py`

A typed compute DAG (the "compiler-side" declarative half). All frozen, tuple-valued,
content-addressed, fully validated.

### 3.1 `DataHandle`
A **reference** to materializable data — never the data itself (air-gap: the grammar
embeds locators, not values).

| field | type | notes |
|---|---|---|
| `kind` | `Literal["data_handle"]` | discriminator for the input union |
| `ref` | `str` | opaque dataset/column locator, e.g. `"tcga:methylation:cg12345"`; `min_length=1` |
| `expected_dimension` | `Dimension \| None` | optional declared dimension of the resolved data |

### 3.2 `NodeRef`
A reference to an upstream node's output (the edges of the DAG).

| field | type | notes |
|---|---|---|
| `kind` | `Literal["node_ref"]` | discriminator |
| `node_id` | `str` | id of an upstream `OperationNode`; `min_length=1` |

`OpInput = Annotated[Union[DataHandle, NodeRef], Field(discriminator="kind")]`.

### 3.3 `ProducedLeafSpec`
Declares the **type** of the L0 `Leaf` a node yields — *not* its value. Lets the graph
type-check statically and lets the runtime wrap an executed value into a typed `Leaf`.

| field | type | notes |
|---|---|---|
| `leaf_kind` | `Literal["quantity","categorical","existence","proposition"]` | which `Leaf` variant the node produces |
| `measurement_basis` | `MeasurementBasis \| None` | for `quantity` outputs |
| `unit` | `str \| None` | only meaningful for FUNDAMENTAL quantity (mirrors `QuantityLeaf` discipline) |
| `dimension` | `Dimension \| None` | optional |

Validator: the `unit`/`measurement_basis` legality mirrors `QuantityLeaf._basis_discipline`
(unit only for FUNDAMENTAL; non-quantity kinds carry neither unit nor basis).

### 3.4 `OperationNode`

| field | type | notes |
|---|---|---|
| `id` | `str` | unique within the graph; `min_length=1` |
| `impl` | `str` | versioned dispatch key, e.g. `"builtin::threshold"`, `"builtin::mean"`, `"python::scipy.stats.spearmanr"`; `min_length=1` |
| `inputs` | `tuple[OpInput, ...]` | DataHandles and/or upstream NodeRefs |
| `params` | `tuple[tuple[str, str], ...]` | op parameters as ordered key/value pairs (no dicts); e.g. `(("threshold","0.05"),)` |
| `produces` | `ProducedLeafSpec` | declared output type |
| `oracle_ref` | `str \| None` | **declared-but-unbound slot** for requirement #2 (oracle dossier binds here later) |

### 3.5 `ComputeGraph`

| field | type | notes |
|---|---|---|
| `nodes` | `tuple[OperationNode, ...]` | `min_length=1` |
| `terminal` | `str` | id of the node whose output feeds the criterion |

Validators (all `model_validator(mode="after")`):
1. **unique ids** — node `id`s are distinct.
2. **acyclic** — the `NodeRef` edges form a DAG (Kahn / DFS).
3. **resolvable refs** — every `NodeRef.node_id` and `terminal` names an existing node.

Properties:
- `topological_order -> tuple[str, ...]` — deterministic topo sort (ties broken by node
  declaration order, so the order is reproducible / content-stable).
- `content_hash -> str` — SHA-256 over canonical node content (mirrors
  `Proposition.content_hash`).

### 3.6 `SatisfactionCriterion`
Turns the terminal node's produced `Leaf` into a 3-valued verdict.

| field | type | notes |
|---|---|---|
| `comparator` | `Comparator` enum | `LT, LE, EQ, NE, GE, GT, WITHIN_TOL` |
| `threshold` | `float \| None` | compare-to-scalar route |
| `reference_leaf_index` | `int \| None` | compare-to-pinned-claim-leaf route (typed stat-vs-stat) |
| `tolerance` | `float \| None` | required for `WITHIN_TOL`; optional elsewhere |

Validators:
- **exactly one of** `threshold` / `reference_leaf_index` is set.
- `WITHIN_TOL` requires `tolerance`.

Semantics (applied by the runtime, §4): produces `SATISFIED` / `REFUTED` / `UNDETERMINED`
(UNDETERMINED when the terminal value is unresolved/None). When comparing to a reference
leaf, **dimensions must be equal** if both sides carry one (mismatch → `UNDETERMINED` with
a recorded reason); full UCUM algebra is a fenced follow-on (§7).

### 3.7 `EvaluationPlan`
Bundles the graph + criterion into the single additive Claim field.

| field | type |
|---|---|
| `graph` | `ComputeGraph` |
| `criterion` | `SatisfactionCriterion` |

### 3.8 Claim wiring
Additive-optional, back-compat (mirrors `licensing` / `roles` / `subject`):
```python
Claim.evaluation_plan: EvaluationPlan | None = None
```
No present-only-when gate in this phase (consistent with the additive-field invariant).
`reference_leaf_index`, when used, indexes into `Claim.leaves` — validated at evaluation
time by the runtime, not as a Claim-level cross-field validator (keeps the field additive).

## 4. The runtime — `evaluate.py`

Pure, adapter-injected, infra-free. Imports only from `polymer_grammar` + stdlib + pydantic.

### 4.1 `Adapter` (Protocol)
The materialization/compute boundary — the *only* place data resolution and op execution
live. Reference implementations ship here; real ones live outside the package.

```python
class Adapter(Protocol):
    identity: str  # distinct tag per implementation — drives the air-gap gate
    def execute(self, node: OperationNode,
                inputs: tuple[ExecValue, ...],
                ctx: MaterializationContext) -> ExecValue: ...
```
`ExecValue` is a small frozen carrier: `value: float | str | None` + `dimension: Dimension | None`
(extensible later for vector/array values — see §7). `inputs` are the already-executed
upstream `ExecValue`s (for `NodeRef` inputs) and resolved data (for `DataHandle` inputs);
resolution of a `DataHandle` is the adapter's responsibility.

### 4.2 `evaluate(plan, ctx, adapter) -> EvaluationResult`
Pure single-implementation execution:
1. Walk `plan.graph` in `topological_order`.
2. For each node, gather its input `ExecValue`s (upstream outputs / resolved handles) and
   call `adapter.execute(node, inputs, ctx)`, wrapping the result per `node.produces` into
   a typed `Leaf` (and recording **drift** vs any pinned expectation: abs/rel diff +
   `within_tolerance`).
3. Apply `plan.criterion` to the `terminal` node's output → 3-valued `SatisfactionVerdict`.
4. Return an `EvaluationResult`. **Never raises on a node error** — a failed node yields a
   `NodeEvaluation` with `error` set, propagates `None` downstream, and the verdict
   degrades to `UNDETERMINED` (status `error`/`partial`).

### 4.3 The air-gap gate — `verify(plan, ctx, adapters, *, agreement_tol=…) -> VerifiedEvaluation`
The headline. Structural "no self-licensing":
1. Require `len(adapters) >= 2`.
2. Require **≥2 distinct `identity` tags** — reject (raise `SelfLicensingError`) if all
   results trace to one identity (writer ≠ verifier).
3. Run `evaluate` once per adapter independently.
4. Check **agreement** between the independent results. This uses its own
   `agreement_tol` (default `abs=1e-9`, `rel=1e-6`, ported from v1.2's drift tolerances) —
   **distinct from the criterion's own threshold/tolerance**, which govern the verdict, not
   cross-adapter equality. Agreement holds iff the terminal `ExecValue`s match within
   `agreement_tol` (numeric) or are exactly equal (categorical/None) **and** all verdicts match.
5. **Only on agreement + `SATISFIED`** mint a `Satisfaction(verdict=SATISFIED,
   materialization=ctx)` — the existing L2 model. The gate does **not** assemble
   `Licensing` or set `Status` (that is the protocol's human-port-gated INTEGRATE stage —
   §7, out of scope).
6. On disagreement: return `agreement=False` with a per-adapter disagreement detail; no
   Satisfaction minted.

### 4.4 Reference adapters (shipped, pure, deterministic)
- `IdentityAdapter(identity="identity")` — echoes pinned values injected via `params` /
  resolved handles. The end-to-end smoke target (mirrors v1.2's identity handler), proving
  the plumbing without network or R.
- `ReferenceAdapter(identity="reference")` — an **independent** implementation of a small
  set of builtin `impl`s (`builtin::identity`, `builtin::threshold`, `builtin::mean`) over
  synthetic injected vectors, so agreement can be tested with two *genuinely distinct*
  implementations (and disagreement tested by feeding one a perturbed input).

## 5. Result models (frozen)

- **`ExecValue`** — `value: float | str | None`, `dimension: Dimension | None`.
- **`NodeEvaluation`** — `node_id`, `impl`, `produced: Leaf | None`, `drift: Drift | None`,
  `error: str | None`.
- **`Drift`** — `pinned`, `computed`, `abs_diff`, `rel_diff`, `within_tolerance` (typed port
  of v1.2's `StatDrift`).
- **`EvaluationResult`** — `verdict: SatisfactionVerdict`, `terminal: ExecValue`,
  `nodes: tuple[NodeEvaluation, ...]`, `adapter_identity: str`,
  `status: Literal["complete","partial","error"]`.
- **`VerifiedEvaluation`** — `results: tuple[EvaluationResult, ...]`, `agreement: bool`,
  `satisfaction: Satisfaction | None`, `disagreement: str | None`.

## 6. Data flow

```
Claim.evaluation_plan ──► evaluate(plan, ctx, adapterA) ─► EvaluationResult_A ┐
                     └──► evaluate(plan, ctx, adapterB) ─► EvaluationResult_B ┘
                                                              │
                                              verify(): identities distinct?
                                              terminal values agree? verdicts agree?
                                                              │
                                         agree + SATISFIED ──► mint Satisfaction(σ, M)
                                         disagree ───────────► VerifiedEvaluation(agreement=False, …)
```
The minted `Satisfaction` is exactly the existing `licensing.Satisfaction` — so a downstream
(protocol) consumer can assemble it into a `Licensing` record and flip `Status` to LICENSED,
behind the human-judgment ports. That assembly is **not** in this phase.

## 7. Scope fence — explicitly OUT (documented seams / follow-ons)

- **Real adapters** (PolymerGenomicsAPI / scipy / R subprocess) — live *outside* the
  grammar package; would break dependency-free isolation. The `Adapter` Protocol + `impl`
  dispatch keys are the seam.
- **Oracle credibility dossier (#2)** — only the `OperationNode.oracle_ref` slot is declared
  now; the dossier object + strength-cap binding are a follow-on (now unblocked).
- **Full UCUM dimensional algebra** — Phase 8 checks *dimension equality* only; UCUM
  parsing + dimensional arithmetic enforcement is the carry-forward Phase-8 follow-up.
- **`Licensing` / `Status` assembly + protocol INTEGRATE** — minting a `Satisfaction` is the
  boundary; assembling licensing + flipping status is the protocol's human-port-gated job.
- **`representation_revision` meta-tier (#5)** — separate phase.
- **Vector/array `ExecValue` + vector `Leaf`** — `ExecValue.value` is scalar/categorical now;
  the array case is the standing vector-`Leaf` ingestion gap.

## 8. Testing

`cd grammar && uv run pytest -q` + `uv run ruff check src tests`. TDD throughout.

**`test_operations.py`** (IR):
- frozen / `extra="forbid"` / tuple discipline holds.
- `ComputeGraph` validators: unique ids, acyclicity (reject a cycle), resolvable
  `NodeRef`/`terminal` (reject a dangling ref).
- `topological_order` deterministic; `content_hash` stable + order-insensitive where intended.
- `ProducedLeafSpec` unit/basis legality mirrors `QuantityLeaf`.
- `SatisfactionCriterion`: exactly-one-of threshold/reference; `WITHIN_TOL` requires tolerance.
- `Claim.evaluation_plan` additive/optional (a Claim with no plan still builds).

**`test_evaluate.py`** (runtime):
- topo execution order; typed `Leaf` wrapping per `produces`.
- 3-valued criterion: SATISFIED / REFUTED / UNDETERMINED (incl. None-propagation on a node error).
- drift recorded vs pinned expectation.
- dimension-mismatch on reference comparison → UNDETERMINED with reason.
- **air-gap:** two distinct-identity adapters agreeing → Satisfaction minted; **same-identity
  → `SelfLicensingError`**; perturbed input → `agreement=False`, no Satisfaction.
- `IdentityAdapter` end-to-end smoke.

**`test_isolation.py`** stays green (no new infra imports).

## 9. Connections

- Unblocks unified-spec requirement **#2** (oracle) via `oracle_ref`; feeds the protocol
  runtime's EXECUTE/GROUND (stage 5) and VERIFY (stage 6).
- Closes the L2 loop: the static `Satisfaction`/`Licensing` records finally have a
  *producer* that can never self-license.
