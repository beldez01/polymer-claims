# Phase 2a — Local Mean-Difference Execution Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Two genuinely independent local adapters that compute a two-group mean difference from a bundled dataset, so a claim's plan licenses/rejects on a COMPUTED value (not an LLM-asserted const), and the #5 adapter trust registry bites on real agreement.

**Architecture:** Pure new code in the umbrella `polymer_claims` package (the impure layer — it does file I/O). It plugs into the EXISTING grammar seam: `OperationNode.inputs` already carries a `DataHandle(ref=...)`, and the `Adapter` Protocol already delegates DataHandle resolution to the adapter. **Zero grammar/protocol changes.** Spec: `docs/superpowers/specs/2026-06-08-phase2a-execution-adapters-design.md`.

**Tech Stack:** Python 3.12+, stdlib only (`csv`, `statistics`, `functools`) — NO new runtime dependency. `polymer_grammar` (Claim/OperationNode/DataHandle/ExecValue/...), `polymer_protocol` (Corpus/run_cycle/AdapterRegistry/AdapterCredential).

**Verify each task:** `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ -q && uv run --project . ruff check src tests`. ABSOLUTE paths. LOCAL only, no push.

**Confirmed API facts (do not re-derive):**
- `from polymer_grammar import Claim, Status, PendingReason, PatternRef, CategoricalLeaf, EvaluationPlan, ComputeGraph, OperationNode, DataHandle, ProducedLeafSpec, MeasurementBasis, SatisfactionCriterion, Comparator, MaterializationContext, ExecValue` — all exported.
- `OperationNode(id: str, impl: str, inputs: tuple[OpInput,...]=(), params: tuple[tuple[str,str],...]=(), produces: ProducedLeafSpec)`. `DataHandle(kind="data_handle", ref: str, expected_dimension=None)`.
- `Adapter` is a structural `Protocol`: an adapter just needs `identity: str` and `execute(self, node: OperationNode, upstream: tuple[ExecValue,...], ctx: MaterializationContext) -> ExecValue`. No subclassing needed. The evaluator catches exceptions from `execute` and degrades that node to an error (verdict UNDETERMINED) — it does NOT crash.
- `ExecValue(value: float | str | None = None, dimension=None)`.
- `from polymer_protocol import Corpus, run_cycle, AdapterRegistry, AdapterCredential` — all exported.
- `AdapterCredential(identity: str, owner: str, implementation_hash: str, version: str="v1", trusted: bool=True)`.
- `AdapterRegistry(credentials: tuple[AdapterCredential,...]=())`, `.resolve(identity)`. Independence = both trusted AND different owner AND different implementation_hash. Passed to `run_cycle(corpus, adapters, ctx, adapter_registry=reg)`. Empty/None registry → grammar identity-distinctness only (still licenses).
- `run_cycle(corpus, adapters, ctx, oracles=None, adapter_registry=None, *, budget=None, ...)` — default budget executes selectable PENDING+plan claims.
- Verify how a `Corpus` is constructed by reading `tests/conftest.py` (look at `licensing_corpus`) — most likely `Corpus(claims=(c,))`. Use the same pattern.

---

### Task 1: Bundled dataset + resolver

**Files:**
- Create: `src/polymer_claims/datasets/dose_response.csv`
- Create: `src/polymer_claims/datasets/__init__.py`
- Test: `tests/test_exec_adapters.py`

- [ ] **Step 1: Create the dataset CSV** `src/polymer_claims/datasets/dose_response.csv` with EXACTLY these 12 data rows (high-group `response` mean = 184/6 = 30.6̄; low-group mean = 100/6 = 16.6̄; difference = **14.0** exactly):

```csv
subject,dose,response,mediator1,mediator2
s01,high,30,0.8,0.5
s02,high,32,0.7,0.6
s03,high,28,0.9,0.4
s04,high,34,0.6,0.7
s05,high,31,0.8,0.5
s06,high,29,0.7,0.6
s07,low,18,0.3,0.2
s08,low,16,0.4,0.1
s09,low,20,0.2,0.3
s10,low,15,0.3,0.2
s11,low,17,0.4,0.1
s12,low,14,0.2,0.3
```

- [ ] **Step 2: Write the failing test** in `tests/test_exec_adapters.py`:

```python
from polymer_claims.datasets import load_dataset


def test_load_dataset_returns_columns():
    data = load_dataset("dose_response")
    assert data["dose"][:2] == ["high", "high"]
    assert data["response"][0] == "30"
    assert len(data["response"]) == 12
    assert set(data["dose"]) == {"high", "low"}


def test_load_dataset_unknown_ref_raises():
    import pytest
    with pytest.raises(Exception):
        load_dataset("__nope__")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_exec_adapters.py -q`
Expected: FAIL — no module `polymer_claims.datasets`.

- [ ] **Step 4: Implement the resolver** `src/polymer_claims/datasets/__init__.py`:

```python
"""Bundled datasets for the local real-execution adapters (Phase 2a).

`load_dataset(ref)` resolves a `DataHandle.ref` to the columns of a CSV shipped
alongside this module. Pure stdlib; cached. This is the impure data layer the
real adapters resolve against (the grammar holds only a DataHandle REFERENCE).
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def load_dataset(ref: str) -> dict[str, list[str]]:
    """Return {column_name: [cell, ...]} for the bundled CSV named `<ref>.csv`.
    Raises FileNotFoundError for an unknown ref (the adapter degrades it to a
    node error; it never crashes the run)."""
    path = _DIR / f"{ref}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"no bundled dataset {ref!r} at {path}")
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"dataset {ref!r} is empty")
    cols: dict[str, list[str]] = {k: [] for k in rows[0]}
    for row in rows:
        for k, v in row.items():
            cols[k].append(v)
    return cols
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_exec_adapters.py -q`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/datasets/ tests/test_exec_adapters.py
git commit -m "feat(exec): bundled dose_response dataset + resolver"
```
(End every commit message with a blank line then: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`)

---

### Task 2: The two independent mean-difference adapters

**Files:**
- Create: `src/polymer_claims/exec_adapters.py`
- Test: `tests/test_exec_adapters.py` (append)

- [ ] **Step 1: Write the failing tests** (append to `tests/test_exec_adapters.py`):

```python
from polymer_grammar import (
    DataHandle,
    MaterializationContext,
    MeasurementBasis,
    OperationNode,
    ProducedLeafSpec,
)
from polymer_claims.exec_adapters import StatsPureAdapter, StatsStdlibAdapter

_CTX = MaterializationContext(id="M1", api_version="v1", data_version="dose_response@v1")


def _mean_diff_node(value_col="response", group_col="dose", group_a="high", group_b="low", ref="dose_response"):
    return OperationNode(
        id="n0",
        impl="stats::mean_diff",
        inputs=(DataHandle(ref=ref),),
        params=(
            ("value_col", value_col),
            ("group_col", group_col),
            ("group_a", group_a),
            ("group_b", group_b),
        ),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )


def test_both_adapters_compute_the_same_mean_diff():
    node = _mean_diff_node()
    pure = StatsPureAdapter().execute(node, (), _CTX).value
    stdlib = StatsStdlibAdapter().execute(node, (), _CTX).value
    assert pure == stdlib
    assert abs(pure - 14.0) < 1e-9   # high mean 30.6̄ − low mean 16.6̄ = 14.0


def test_adapter_identities_are_distinct():
    assert StatsPureAdapter().identity == "stats-pure"
    assert StatsStdlibAdapter().identity == "stats-stdlib"
    assert StatsPureAdapter().identity != StatsStdlibAdapter().identity


def test_bad_column_raises_inside_adapter():
    import pytest
    node = _mean_diff_node(value_col="__missing__")
    with pytest.raises(Exception):
        StatsPureAdapter().execute(node, (), _CTX)


def test_unsupported_impl_raises():
    import pytest
    bad = OperationNode(
        id="n0", impl="builtin::const", params=(("value", "1"),),
        produces=ProducedLeafSpec(leaf_kind="quantity", measurement_basis=MeasurementBasis.DERIVED),
    )
    with pytest.raises(Exception):
        StatsStdlibAdapter().execute(bad, (), _CTX)
```

- [ ] **Step 2: Run to verify fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_exec_adapters.py -q`
Expected: FAIL — no module `polymer_claims.exec_adapters`.

- [ ] **Step 3: Implement the adapters** `src/polymer_claims/exec_adapters.py`:

```python
"""Phase 2a real-execution adapters: two GENUINELY INDEPENDENT implementations of a
two-group mean difference computed from a bundled dataset.

They share the DATA-ACCESS layer (`load_dataset` + param extraction) but each computes
the statistic with its OWN code, so agreement between them is a real two-implementation
check (the #5 adapter trust registry enforces owner/impl-hash independence on top). A
fully-separate impl or data source (e.g. numpy, or PolymerGenomicsAPI) swaps in later on
the same seam — this slice proves the machinery, not a specific library.

Umbrella/impure ONLY (file I/O via the dataset resolver). Grammar + protocol untouched.
"""
from __future__ import annotations

import statistics

from polymer_grammar import DataHandle, ExecValue, MaterializationContext, OperationNode

from .datasets import load_dataset

_IMPL = "stats::mean_diff"


def _resolve(node: OperationNode) -> tuple[list[float], list[float]]:
    """Resolve the node's DataHandle + params into (group_a values, group_b values).
    Raises on a bad impl / missing handle / missing column / empty group — the evaluator
    degrades the raise to a node error."""
    if node.impl != _IMPL:
        raise ValueError(f"{_IMPL} adapter cannot execute impl {node.impl!r}")
    handle = next((i for i in node.inputs if isinstance(i, DataHandle)), None)
    if handle is None:
        raise ValueError(f"{_IMPL} requires a DataHandle input")
    p = {k: v for k, v in node.params}
    value_col, group_col = p["value_col"], p["group_col"]
    group_a, group_b = p["group_a"], p["group_b"]
    data = load_dataset(handle.ref)
    if value_col not in data or group_col not in data:
        raise KeyError(f"dataset {handle.ref!r} missing column {value_col!r}/{group_col!r}")
    groups = data[group_col]
    values = data[value_col]
    a = [float(v) for v, g in zip(values, groups) if g == group_a]
    b = [float(v) for v, g in zip(values, groups) if g == group_b]
    if not a or not b:
        raise ValueError(f"empty group ({group_a!r}={len(a)}, {group_b!r}={len(b)})")
    return a, b


class StatsPureAdapter:
    """Independent impl A — hand-rolled accumulation (no statistics module)."""

    identity = "stats-pure"

    def execute(
        self, node: OperationNode, upstream: tuple[ExecValue, ...], ctx: MaterializationContext
    ) -> ExecValue:
        a, b = _resolve(node)
        mean_a = sum(a) / len(a)
        mean_b = sum(b) / len(b)
        return ExecValue(value=mean_a - mean_b)


class StatsStdlibAdapter:
    """Independent impl B — uses the stdlib `statistics` module."""

    identity = "stats-stdlib"

    def execute(
        self, node: OperationNode, upstream: tuple[ExecValue, ...], ctx: MaterializationContext
    ) -> ExecValue:
        a, b = _resolve(node)
        return ExecValue(value=statistics.fmean(a) - statistics.fmean(b))
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_exec_adapters.py -q`
Expected: PASS (all Task 1 + Task 2 tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/exec_adapters.py tests/test_exec_adapters.py
git commit -m "feat(exec): independent stats-pure + stats-stdlib mean_diff adapters"
```

---

### Task 3: Plan-builder + integration through `run_cycle` (license / reject / independence gate)

**Files:**
- Modify: `src/polymer_claims/exec_adapters.py` (add `mean_diff_claim` + a credentials helper)
- Test: `tests/test_exec_adapters.py` (append)

- [ ] **Step 1: Write the failing integration tests** (append to `tests/test_exec_adapters.py`). FIRST read `tests/conftest.py` to confirm how a `Corpus` is constructed (e.g. `licensing_corpus`) and mirror it; the code below assumes `Corpus(claims=(c,))` — adjust to the real constructor if different:

```python
from polymer_grammar import Comparator, Status
from polymer_protocol import AdapterCredential, AdapterRegistry, Corpus, run_cycle
from polymer_claims.exec_adapters import independent_registry, mean_diff_claim

_ADAPTERS = (StatsPureAdapter(), StatsStdlibAdapter())


def _status(result, claim_id):
    return next(c.status for c in result.corpus.claims if c.id == claim_id)


def test_true_claim_licenses_on_computed_value():
    # true mean_diff is 14.0; criterion gt 10 -> SATISFIED
    c = mean_diff_claim("c-true", comparator=Comparator.GT, threshold=10.0)
    result = run_cycle(Corpus(claims=(c,)), _ADAPTERS, _CTX, adapter_registry=independent_registry())
    assert _status(result, "c-true") == Status.LICENSED


def test_false_claim_is_rejected_on_computed_value():
    # 14.0 is NOT > 20 -> REFUTED -> rejected
    c = mean_diff_claim("c-false", comparator=Comparator.GT, threshold=20.0)
    result = run_cycle(Corpus(claims=(c,)), _ADAPTERS, _CTX, adapter_registry=independent_registry())
    assert _status(result, "c-false") == Status.REJECTED


def test_same_owner_pair_is_held_pending_by_independence_gate():
    c = mean_diff_claim("c-dep", comparator=Comparator.GT, threshold=10.0)
    same_owner = AdapterRegistry(credentials=(
        AdapterCredential(identity="stats-pure", owner="same", implementation_hash="h-pure"),
        AdapterCredential(identity="stats-stdlib", owner="same", implementation_hash="h-stdlib"),
    ))
    result = run_cycle(Corpus(claims=(c,)), _ADAPTERS, _CTX, adapter_registry=same_owner)
    # would-be-licensed claim is withheld because the two adapters are NOT independent
    assert _status(result, "c-dep") == Status.PENDING
```

- [ ] **Step 2: Run to verify fail**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_exec_adapters.py -q`
Expected: FAIL — `mean_diff_claim` / `independent_registry` not defined.

- [ ] **Step 3: Implement the builder + registry helper** — append to `src/polymer_claims/exec_adapters.py`:

```python
from polymer_grammar import (  # noqa: E402  (grouped with the builder additions)
    CategoricalLeaf,
    Claim,
    ComputeGraph,
    DataHandle as _DataHandle,
    EvaluationPlan,
    MeasurementBasis as _MB,
    OperationNode as _OperationNode,
    PatternRef,
    PendingReason,
    ProducedLeafSpec as _ProducedLeafSpec,
    SatisfactionCriterion,
    Status,
    Comparator,
)
from polymer_protocol import AdapterCredential, AdapterRegistry


def mean_diff_claim(
    claim_id: str,
    *,
    value_col: str = "response",
    group_col: str = "dose",
    group_a: str = "high",
    group_b: str = "low",
    comparator: Comparator = Comparator.GT,
    threshold: float = 10.0,
    ref: str = "dose_response",
    title: str = "high vs low dose mean difference",
    ontology_term: str = "dose-response",
) -> Claim:
    """Build a PENDING Claim whose plan computes `mean_diff` over a bundled dataset.
    (In Phase 2b the LLM emits these; here they're constructed directly.)"""
    node = _OperationNode(
        id="n0",
        impl="stats::mean_diff",
        inputs=(_DataHandle(ref=ref),),
        params=(
            ("value_col", value_col),
            ("group_col", group_col),
            ("group_a", group_a),
            ("group_b", group_b),
        ),
        produces=_ProducedLeafSpec(leaf_kind="quantity", measurement_basis=_MB.DERIVED),
    )
    plan = EvaluationPlan(
        graph=ComputeGraph(nodes=(node,), terminal="n0"),
        criterion=SatisfactionCriterion(comparator=comparator, threshold=threshold),
    )
    return Claim(
        id=claim_id,
        title=title,
        pattern=PatternRef(id="adjusted_effect", version="v1"),
        leaves=(CategoricalLeaf(ontology_term=ontology_term),),
        status=Status.PENDING,
        pending_reason=PendingReason.UNTESTED,
        evaluation_plan=plan,
    )


def independent_registry() -> AdapterRegistry:
    """Trust credentials asserting the two adapters are genuinely independent
    (distinct owners + impl hashes), so the #5 gate licenses on their agreement."""
    return AdapterRegistry(credentials=(
        AdapterCredential(identity="stats-pure", owner="owner-pure", implementation_hash="h-pure"),
        AdapterCredential(identity="stats-stdlib", owner="owner-stdlib", implementation_hash="h-stdlib"),
    ))
```

NOTE: consolidate imports cleanly — fold the new `polymer_grammar` names into the module's existing import block at the top rather than a second import statement if ruff complains about E402/duplicate imports; the aliased names above (`_DataHandle` etc.) avoid clashing with the top-of-file `DataHandle`/`OperationNode` used by `_resolve`. Either approach is fine as long as `ruff check` is clean.

- [ ] **Step 4: Run to verify pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_exec_adapters.py -q`
Expected: PASS (all tests). If `test_same_owner_pair...` does not return PENDING, re-read `protocol/src/polymer_protocol` `verify_stage` for the exact held-status semantics and adjust the assertion to the real behavior (status PENDING with `pending_reason` for not-independent) — do NOT change the gate.

- [ ] **Step 5: Lint + commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
uv run --project . ruff check src tests
git add src/polymer_claims/exec_adapters.py tests/test_exec_adapters.py
git commit -m "feat(exec): mean_diff_claim builder + run_cycle integration (license/reject/independence gate)"
```

---

### Task 4: Packaging (ship the CSV) + full gate

**Files:**
- Modify: `pyproject.toml` (umbrella, repo root) — include package data
- Verify: build + install smoke

- [ ] **Step 1: Confirm the CSV ships in the wheel.** Read the root `pyproject.toml` build-system. Build the wheel and check the CSV is included:

```bash
cd /Users/zbb2/Desktop/polymer-claims
uv build --wheel 2>&1 | tail -3
python -c "import zipfile,glob; w=sorted(glob.glob('dist/*.whl'))[-1]; print('dose_response.csv' in '\n'.join(zipfile.ZipFile(w).namelist()))"
```
Expected: prints `True`. If `False`, add package-data inclusion to `pyproject.toml` matching the build backend (e.g. for hatchling: `[tool.hatch.build.targets.wheel.force-include]` or an `artifacts`/`include` entry covering `src/polymer_claims/datasets/*.csv`; for setuptools: `[tool.setuptools.package-data]` `polymer_claims = ["datasets/*.csv"]`). Re-run until `True`.

- [ ] **Step 2: Install smoke reads the bundled data.** Confirm the installed wheel can resolve the dataset (not just the source tree):

```bash
cd /Users/zbb2/Desktop/polymer-claims && bash scripts/build_and_test_install.sh 2>&1 | tail -5
```
Expected: ends with the existing SUCCESS line. Then additionally verify in the throwaway venv style — if `build_and_test_install.sh` does not already import the package, add a one-line check there OR run: build the wheel, `pip install` it into a fresh `python -m venv`, and `python -c "from polymer_claims.datasets import load_dataset; print(len(load_dataset('dose_response')['response']))"` → prints `12`. (This proves the CSV ships AND resolves from an installed location.)

- [ ] **Step 3: Full green gate.**

```bash
cd /Users/zbb2/Desktop/polymer-claims && bash scripts/check-all.sh 2>&1 | tail -5
```
Expected: `ALL GREEN`.

- [ ] **Step 4: Commit (if pyproject changed).**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add pyproject.toml
git commit -m "build: ship dose_response.csv package data for the exec adapters"
```
(Skip if `pyproject.toml` was unchanged because the backend already includes package data.)

---

## After all tasks

- `bash scripts/check-all.sh` ALL GREEN + the install smoke reads the bundled CSV.
- Finish the branch with superpowers:finishing-a-development-branch (local merge no-ff to `main`, NO push — matching this repo's convention).
- Update `docs/superpowers/CONTINUE.md` (Phase 2a done; NEXT = 2b LLM real-data DSL) and the knowledge-protocol memory.

## Self-Review

- **Spec coverage:** dataset+resolver (Task 1) ✓; `stats::mean_diff` two independent adapters (Task 2) ✓; credentials + plan-builder + run_cycle license/reject/independence-gate (Task 3) ✓; packaging/CSV-ships + full gate (Task 4) ✓; scope fences (no LLM/oracle/API/serve, no new dep) respected — none of those appear in any task. ✓
- **No placeholders:** every code step shows complete code; the CSV is given verbatim; commands have expected output. ✓
- **Type consistency:** `mean_diff_claim`/`independent_registry`/`load_dataset`/`StatsPureAdapter`/`StatsStdlibAdapter` names match across tasks; `stats::mean_diff` impl string and the param keys (`value_col`/`group_col`/`group_a`/`group_b`) are identical in the adapter, the builder, and the tests; the true value 14.0 is consistent (threshold 10 licenses, 20 rejects). ✓
- **Grammar/protocol untouched:** all new files are umbrella; no task edits `grammar/` or `protocol/`. ✓
