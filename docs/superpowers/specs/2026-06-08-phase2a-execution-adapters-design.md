# Phase 2a — Local mean-difference execution adapters (design)

**Date:** 2026-06-08 · **Branch:** `feat/exec-adapters-2a` · **Status:** approved design

## Context

The live agent loop (`serve --llm`) generates real claims that license/reject end-to-end, but on the **deterministic reference substrate**: every claim's plan is `builtin::const`, so the value it "computes" is a number the LLM *asserted*, not one derived from data. The plumbing is real; the science is not. This is the long-standing honesty caveat.

Phase 2 replaces that substrate with **execution adapters that compute a claim's verdict from real data**, so a generated plan's verdict reflects the world. Phase 2 was decomposed (user decision, 2026-06-08) into:

- **2a (this spec):** a local stats adapter pair over a bundled dataset — proves the real-execution machinery + genuine adapter independence, self-contained and in-CI.
- **2b:** extend the LLM DSL so the agent proposes real-data plans (not just const).
- **2c:** an oracle dossier for the apparatus, capping the generated claim's `ValidationTier` (#2).
- **2d:** PolymerGenomicsAPI as a second real data source on the same adapter seam.

## Goal

Ship two **genuinely independent** local adapters that compute a **two-group mean difference** from a bundled dataset, so a claim whose plan is `stats::mean_diff` licenses or rejects based on a **computed** value — and the adapter trust registry (#5) finally bites on *real* agreement between independent implementations.

## Key finding: no grammar or protocol changes

The seam already exists. `OperationNode.inputs` supports `DataHandle(kind="data_handle", ref: str, expected_dimension)` — "a REFERENCE to materializable data — never the data itself (air-gap)." The `Adapter` Protocol (`grammar/evaluate.py`) states: *"Resolving DataHandle inputs is the adapter's own responsibility."* The reference adapters (`IdentityAdapter`/`ReferenceAdapter`) only handle `builtin::const|identity|mean` from inline params; a **real** adapter reads `node.inputs` for a `DataHandle`, resolves it to the dataset, and computes. `verify()` already runs a plan under ≥2 distinct-identity adapters and mints a `Satisfaction` only on agreement + SATISFIED. `run_cycle(corpus, adapters, ctx, oracles=None, adapter_registry=None, ...)` already accepts the adapter tuple + the trust registry.

Therefore **Phase 2a is pure new umbrella (`polymer_claims`) code** (it does file I/O — the impure layer). Grammar and protocol stay byte-untouched; the grammar-isolation invariant is preserved.

## Components

All under `src/polymer_claims/`:

1. **Bundled dataset** — `src/polymer_claims/datasets/dose_response.csv`: a small fixed (synthetic-but-real) table, ~50 rows, columns `subject, dose, response, mediator1, mediator2` where `dose ∈ {high, low}`. Ground truth is known by construction, so some mean-diff claims are true (license) and some false (reject). It is checked into the repo (committed package data).

2. **Dataset resolver** — `src/polymer_claims/datasets/__init__.py` (or `dataset_registry.py`): maps a `DataHandle.ref` (e.g. `"dose_response"`) to the loaded columns. Pure-stdlib `csv` read; small, cached. The `ref` is the dataset id (column selection is via the node's `params`, below). Unknown `ref` → raise (the adapter surfaces it as a node error → UNDETERMINED, not a crash).

3. **`stats::mean_diff` operation contract** — an `OperationNode` with:
   - `impl = "stats::mean_diff"`
   - `inputs = (DataHandle(ref="dose_response"),)`
   - `params = (("value_col","response"), ("group_col","dose"), ("group_a","high"), ("group_b","low"))`
   The adapter resolves the handle, reads `value_col` partitioned by `group_col`, computes `mean(value_col | group==group_a) − mean(value_col | group==group_b)`, returns `ExecValue(value=<float>)`. The existing `SatisfactionCriterion` (e.g. `gt 10`) then turns that into SATISFIED/REFUTED — unchanged machinery, but on a **computed** value.

4. **Two independent adapters** — both implement the grammar `Adapter` Protocol (`execute(node, upstream, ctx) -> ExecValue`):
   - `StatsPureAdapter` (`identity="stats-pure"`) — hand-rolled sums/length.
   - `StatsStdlibAdapter` (`identity="stats-stdlib"`) — Python's `statistics.mean`.
   Genuinely different implementations, **no new runtime dependency** (both stdlib; a numpy/scipy adapter can swap in later — 2a is about the seam + independence, not the library). Each only handles `impl=="stats::mean_diff"` (and may delegate/raise otherwise). Resolving a `DataHandle` they don't recognize → raise → node error.

5. **Adapter credentials** — register the two in an `AdapterRegistry` with **distinct `owner` and `implementation_hash`** (both `trusted=True`), so `adapters_independent` is true and the #5 gate licenses; a constructed *same-owner* pair is held PENDING (gate bites). Credentials are operator-asserted (the registry is the authority — an adapter can't declare its own owner).

6. **Plan-builder helper** — `mean_diff_claim(...)` constructs a PENDING `Claim` carrying a `stats::mean_diff` `EvaluationPlan` + `DataHandle` + `SatisfactionCriterion`. Used by tests and an optional demo. **The LLM emitting such plans is the 2b slice** — 2a exercises the machinery with constructed plans.

## Data flow

```
mean_diff_claim(value_col, group_col, group_a, group_b, comparator, threshold, ref)
        │  PENDING + plan
        ▼
run_cycle(corpus, adapters=(StatsPureAdapter(), StatsStdlibAdapter()),
          ctx, adapter_registry=reg)
        │  SELECT → EXECUTE(verify) runs BOTH adapters on the plan
        ▼
both resolve DataHandle → load dose_response.csv → compute mean_diff
   agree (within tol) AND criterion SATISFIED  → Satisfaction → LICENSED
   agree AND criterion REFUTED                 → REJECTED
   disagree                                    → no Satisfaction (not licensed)
   same-owner pair under the registry          → held PENDING (ADAPTER_NOT_INDEPENDENT)
```

`ctx` is a `MaterializationContext(id, api_version, data_version)`; `data_version` pins the dataset version, so the minted `Satisfaction.materialization` records which dataset version licensed the claim (and the #5a DRIFT daemon can later re-open it if the dataset version moves).

## Error handling

A bad `ref`, missing column, or empty group → the adapter raises → the evaluator already catches per-node exceptions and degrades that node to an `error` (status `partial`/`error`, verdict UNDETERMINED) → the claim does not license, no crash. Covered by a test.

## Testing

- **Unit (adapters):** `mean_diff` correct on the known CSV for both adapters; the two agree; a refuting threshold yields REFUTED; a bad column/ref degrades to a node error (no raise out of `verify`).
- **Integration (`run_cycle`):** a true mean-diff claim LICENSES; a false one is REJECTED; a *same-owner* credential pair is held PENDING (`ADAPTER_NOT_INDEPENDENT`) — the #5 gate bites on real computation; an independent pair licenses.
- **Isolation / gate:** grammar + protocol untouched; `bash scripts/check-all.sh` ends ALL GREEN; `bash scripts/build_and_test_install.sh` still green (new dataset ships as package data; no new dependency; core import stays clean).

## Files

- New: `src/polymer_claims/exec_adapters.py` (the two adapters + credentials helper + `mean_diff_claim` builder), `src/polymer_claims/datasets/__init__.py` (resolver), `src/polymer_claims/datasets/dose_response.csv` (data).
- New tests: `tests/test_exec_adapters.py` (unit + integration).
- Packaging: ensure `*.csv` ships in the wheel (package-data / `pyproject.toml` include) so the install smoke can read it.

## Scope fences (explicitly NOT in 2a)

- **No LLM** proposing real-data plans → **2b** (constrained DSL extension: `impl` + `DataHandle` ref + column params, with validation).
- **No oracle dossier / ValidationTier cap** on the apparatus → **2c**.
- **No PolymerGenomicsAPI** / network data → **2d** (plugs into the same `Adapter` seam).
- **No `serve`/viewer change** in 2a (an optional local demo script may construct + run a real claim; live integration arrives with 2b).
- **No new runtime dependency** (stdlib only).

## Verification (end-to-end)

1. `bash scripts/check-all.sh` → ALL GREEN.
2. `bash scripts/build_and_test_install.sh` → installed wheel reads the bundled CSV; core CLI clean without `[serve]/[llm]`.
3. A demo (test or short script): build a true `mean_diff` claim → `run_cycle` with the two independent adapters → it LICENSES with a `Satisfaction` whose value was *computed* from the CSV; flip the threshold → REJECTED; swap to a same-owner credential pair → held PENDING.
