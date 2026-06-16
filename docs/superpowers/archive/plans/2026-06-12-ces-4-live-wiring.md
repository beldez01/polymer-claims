# CES-4 Live Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the running `NodeRunner`/`serve` loop record each live license's content-address and run the drift daemon — world moves → claim re-opens → next cycle re-licenses against the new world.

**Architecture:** Umbrella-only. Reuse the existing pure protocol entry points (`run_cycle(materializations=)`, `drift_pass`, `reopen_drifted`, `next_action`) and the umbrella `materialization_map`. New: a `clear_contract_cache()` helper, an opt-in `content_address` flag + `refresh_world()` + a `DRIFT` arm on `NodeRunner`, and a `POST /refresh` endpoint with drift fields on `/status`. Grammar and protocol packages are untouched; Corpus stays 4. Default off → every existing test stays byte-identical.

**Tech Stack:** Python, pydantic v2 (frozen models), pytest, FastAPI (`[serve]` extra). Spec: `docs/specs/2026-06-12-ces-4-live-wiring-design.md`.

---

## File Structure

- **Modify** `src/polymer_claims/contracts/__init__.py` — add public `clear_contract_cache()` (busts the `_load_contract` lru-cache).
- **Modify** `src/polymer_claims/node.py` — `content_address`/`profiles` params; recording half (`materializations=` into `run_cycle`); `self.current` + `refresh_world()`; `DRIFT` arm in `tick`; `self.last_drift`/`self.n_reopened` state.
- **Modify** `src/polymer_claims/server.py` — `POST /refresh`; `_drift_status()` helper; drift fields on `_status()`.
- **Modify** `tests/conftest.py` — `methyl_node(**kwargs)` helper (one-claim content-addressed methylation corpus).
- **Create** `tests/test_node_content_address.py` — recording + `refresh_world` + drift-arm + flywheel tests.
- **Modify** `tests/test_server.py` — `/refresh` + `/status` drift tests.
- **Create** `tests/test_clear_contract_cache.py` — cache-bust unit test.

Background facts the implementer needs (already verified against the code):
- `execute_ground` (`protocol/src/polymer_protocol/execute.py:57`) does `ctx_c = materializations.get(c.id, ctx) if materializations else ctx` — an empty/`None` map is a no-op.
- `run_cycle` (`protocol/src/polymer_protocol/cycle.py`) accepts a keyword `materializations=`.
- The lru-cache is on the **private** `_load_contract(uid)` (`contracts/__init__.py:64`), NOT on `load_contract`.
- `materialization_map(corpus, base_ctx, *, profiles=(CANONICAL_EPICV2_V1,))` returns `{claim_id: MaterializationContext}`; a claim with no resolvable contract gets NO entry.
- `materialization.py` binds `load_contract` into its own namespace at import — tests that simulate a moved dataset must monkeypatch `polymer_claims.materialization.load_contract`, NOT `polymer_claims.contracts.load_contract`.
- A content-addressed methylation claim that licenses on a single cycle (from `tests/test_ces3_content_address_e2e.py`): `region_delta_beta_claim("c-true", threshold=0.10)`, adapters `(RegionMeanDiffAdapter(), RegionLmCoefAdapter())`, `adapter_registry=methyl_independent_registry()`, `oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public"))`, ctx `MaterializationContext(id="M", api_version="v1", data_version="d1")`. Its default contract ref resolves to `se:epicv2_casectrl_demo@1`.

---

## Task 1: `clear_contract_cache()` helper

**Files:**
- Modify: `src/polymer_claims/contracts/__init__.py`
- Test: `tests/test_clear_contract_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_clear_contract_cache.py
from polymer_claims.contracts import _load_contract, clear_contract_cache, load_contract


def test_clear_contract_cache_resets_lru():
    load_contract("se:epicv2_casectrl_demo@1")
    assert _load_contract.cache_info().currsize >= 1
    clear_contract_cache()
    assert _load_contract.cache_info().currsize == 0
    # still works after a clear (re-reads disk)
    assert load_contract("se:epicv2_casectrl_demo@1").dimnames_hash.startswith("sha256:")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_clear_contract_cache.py -v`
Expected: FAIL with `ImportError: cannot import name 'clear_contract_cache'`.

- [ ] **Step 3: Add the helper**

In `src/polymer_claims/contracts/__init__.py`, after `_load_contract` (the cached function ending at line ~99), add:

```python
def clear_contract_cache() -> None:
    """Drop the bundled-contract lru-cache so the next load_contract re-reads disk
    (a node refresh after a dataset is re-published)."""
    _load_contract.cache_clear()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_clear_contract_cache.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/contracts/__init__.py tests/test_clear_contract_cache.py
git commit -m "feat(contracts): clear_contract_cache — bust the bundled-contract lru-cache"
```

---

## Task 2: NodeRunner recording half (`content_address` flag + `materializations=`)

**Files:**
- Modify: `src/polymer_claims/node.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_node_content_address.py`

- [ ] **Step 1: Add the conftest helper**

In `tests/conftest.py`, ensure `MaterializationContext` is importable (add it to the existing `from polymer_grammar import (...)` block if absent), then append:

```python
def methyl_node(**kwargs):
    """A NodeRunner over a one-claim content-addressed methylation corpus that licenses on a
    single cycle (the CES-2/CES-3 apparatus). content_address defaults ON. Heavy imports
    (numpy-backed methyl adapters) are local so importing conftest stays numpy-free."""
    from polymer_grammar import MaterializationContext

    from polymer_claims.analysis_profile import profile_oracle_registry
    from polymer_claims.methyl_adapters import (
        RegionLmCoefAdapter,
        RegionMeanDiffAdapter,
        methyl_independent_registry,
        region_delta_beta_claim,
    )
    from polymer_claims.node import NodeRunner
    from polymer_claims.profiles import CANONICAL_EPICV2_V1

    claim = region_delta_beta_claim("c-true", threshold=0.10)
    corpus = Corpus(claims=(claim,), fdr_ledger=FDRLedger(target_fdr=0.05))
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    return NodeRunner(
        corpus,
        adapters=(RegionMeanDiffAdapter(), RegionLmCoefAdapter()),
        ctx=base,
        content_address=kwargs.pop("content_address", True),
        adapter_registry=methyl_independent_registry(),
        oracles=profile_oracle_registry((CANONICAL_EPICV2_V1, "recomputable_public")),
        **kwargs,
    )
```

(`Corpus` and `FDRLedger` are already imported in conftest. If `FDRLedger` is not, add it to the `polymer_grammar` import.)

- [ ] **Step 2: Write the failing test**

```python
# tests/test_node_content_address.py
from __future__ import annotations

from polymer_grammar import PendingReason, Status

from tests.conftest import methyl_node


def test_content_addressed_node_records_address_on_license():
    r = methyl_node()  # content_address=True
    for _ in range(3):
        r.tick()
    c = next(x for x in r.corpus.claims if x.id == "c-true")
    assert c.status == Status.LICENSED
    m = c.licensing.satisfactions[0].materialization
    assert m.dimnames_hash is not None
    assert m.profile_hash is not None
    assert m.semantic_run_id is not None and m.semantic_run_id.startswith("sha256:")


def test_node_without_content_address_records_no_address():
    r = methyl_node(content_address=False)
    for _ in range(3):
        r.tick()
    c = next(x for x in r.corpus.claims if x.id == "c-true")
    assert c.status == Status.LICENSED
    m = c.licensing.satisfactions[0].materialization
    assert m.dimnames_hash is None
    assert m.profile_hash is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_node_content_address.py -v`
Expected: FAIL — `NodeRunner.__init__() got an unexpected keyword argument 'content_address'`.

- [ ] **Step 4: Wire the recording half**

In `src/polymer_claims/node.py`:

(a) Add imports near the existing umbrella-free imports (top of file, after the protocol import block):

```python
from .materialization import materialization_map
from .profiles import CANONICAL_EPICV2_V1
```

(b) Add `content_address` and `profiles` params to **both** `__init__` and `from_seed` signatures (mirror the existing keyword-only style), e.g. in `__init__`:

```python
        max_frames: int | None = 10000,
        content_address: bool = False,
        profiles: tuple = (CANONICAL_EPICV2_V1,),
        **run_cycle_kwargs,
```

and store them in `__init__` (before the frame-0 block):

```python
        self.content_address = content_address
        self.profiles = profiles
```

In `from_seed`, add the same two params and pass them through:

```python
        return cls(
            corpus,
            adapters=adapters,
            ctx=ctx,
            config=config,
            scheduler_budget=scheduler_budget,
            max_frames=max_frames,
            content_address=content_address,
            profiles=profiles,
            **run_cycle_kwargs,
        )
```

(c) In `tick`, replace the `RUN_CYCLE` call so it threads the per-claim map:

```python
        if action is not None and action.kind == ActionKind.RUN_CYCLE:
            mats = (
                materialization_map(self.corpus, self.ctx, profiles=self.profiles)
                if self.content_address
                else None
            )
            result = run_cycle(
                self.corpus,
                self.adapters,
                self.ctx,
                ledger=self.ledger,
                materializations=mats,
                **self.run_cycle_kwargs,
            )
            self.corpus = result.corpus
            self.ledger = result.ledger
            n_frontier = len(result.frontier)
            n_added = len(result.generation.admitted)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_node_content_address.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Run the existing node tests for back-compat**

Run: `python -m pytest tests/test_node.py -v`
Expected: PASS (unchanged — default `content_address=False`).

- [ ] **Step 7: Commit**

```bash
git add src/polymer_claims/node.py tests/conftest.py tests/test_node_content_address.py
git commit -m "feat(node): record content-address on live licenses (opt-in content_address)"
```

---

## Task 3: `refresh_world()` + `self.current`

**Files:**
- Modify: `src/polymer_claims/node.py`
- Test: `tests/test_node_content_address.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_node_content_address.py`:

```python
def test_refresh_world_tracks_current_address(monkeypatch):
    r = methyl_node()  # content_address=True -> __init__ set self.current
    real = r.current.dimnames_hash
    assert real is not None and real.startswith("sha256:")
    # unchanged disk -> same address
    assert r.refresh_world().dimnames_hash == real

    # simulate a re-published dataset: a contract with a moved dimnames_hash, valid betas path
    import polymer_claims.materialization as mat_mod
    from polymer_claims.contracts import load_contract as real_load

    moved = "sha256:" + "b" * 64
    monkeypatch.setattr(
        mat_mod, "load_contract",
        lambda ref: real_load(ref).model_copy(update={"dimnames_hash": moved}),
    )
    assert r.refresh_world().dimnames_hash == moved


def test_refresh_world_off_when_not_content_addressed():
    r = methyl_node(content_address=False)
    # self.current falls back to the seed ctx (no content-address fields)
    assert r.current.dimnames_hash is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_node_content_address.py -k refresh_world -v`
Expected: FAIL — `AttributeError: 'NodeRunner' object has no attribute 'current'` / `refresh_world`.

- [ ] **Step 3: Implement `refresh_world` + init `self.current`**

In `src/polymer_claims/node.py`:

(a) Extend the imports to bring in the cache-buster and the drift types (used here + Task 4):

```python
from .contracts import clear_contract_cache
```
and from the protocol drift module:
```python
from polymer_protocol.drift import DriftRecord, drift_pass, reopen_drifted
```

(b) At the END of `__init__` (after `self._licensed_prev = n_licensed(corpus)`), add the drift/world state:

```python
        self.last_drift: DriftRecord | None = None
        self.n_reopened: int = 0
        if self.content_address:
            self.refresh_world()
        else:
            self.current = self.ctx
```

(c) Add the method (place it just above `tick`):

```python
    def refresh_world(self) -> MaterializationContext:
        """Re-read the live SE-Contracts/profile and recompute the current-world content-address.
        Operator/endpoint-triggered (not per-tick): busts the contract cache so a re-published
        dataset is actually re-read, then takes the v1 single-world representative (all entries of
        a single-dataset corpus share one address). Empty map -> the seed ctx (drift inert)."""
        clear_contract_cache()
        m = materialization_map(self.corpus, self.ctx, profiles=self.profiles)
        self.current = next(iter(m.values()), self.ctx)
        return self.current
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_node_content_address.py -k refresh_world -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/node.py tests/test_node_content_address.py
git commit -m "feat(node): refresh_world — recompute current-world content-address from disk"
```

---

## Task 4: The `DRIFT` arm in `tick`

**Files:**
- Modify: `src/polymer_claims/node.py`
- Test: `tests/test_node_content_address.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_node_content_address.py`:

```python
def test_drift_arm_reopens_after_world_moves(monkeypatch):
    r = methyl_node()
    for _ in range(3):
        r.tick()
    c = next(x for x in r.corpus.claims if x.id == "c-true")
    assert c.status == Status.LICENSED

    import polymer_claims.materialization as mat_mod
    from polymer_claims.contracts import load_contract as real_load

    monkeypatch.setattr(
        mat_mod, "load_contract",
        lambda ref: real_load(ref).model_copy(update={"dimnames_hash": "sha256:" + "b" * 64}),
    )
    r.refresh_world()        # current now points at the moved dataset
    r.tick()                 # scheduler should recommend DRIFT

    c = next(x for x in r.corpus.claims if x.id == "c-true")
    assert c.status == Status.PENDING
    assert c.pending_reason == PendingReason.MATERIALIZATION_DRIFTED
    assert r.n_reopened == 1
    assert r.last_drift is not None
    assert any(f.claim_id == "c-true" for f in r.last_drift.drifted)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_node_content_address.py -k drift_arm -v`
Expected: FAIL — claim stays `LICENSED` (the `DRIFT` recommendation falls through to the IDLE branch; `n_reopened` is 0).

- [ ] **Step 3: Implement the scheduler `current` + the `DRIFT` arm**

In `src/polymer_claims/node.py`, `tick`:

(a) Pass `current` into the scheduler state so the `DRIFT` branch can rank:

```python
        state = SchedulerState(
            corpus=self.corpus,
            ledger=self.ledger,
            proposers_available=self._proposers_available,
            current=self.current if self.content_address else None,
        )
```

(b) Insert a `DRIFT` branch between the `RUN_CYCLE` `if` and the `else` IDLE branch:

```python
        elif action is not None and action.kind == ActionKind.DRIFT:
            _, record = drift_pass(self.corpus, current=self.current)
            self.corpus = reopen_drifted(self.corpus, record)
            self.last_drift = record
            self.n_reopened += len(record.drifted)
            n_frontier = 0
            n_added = 0
```

(The existing `else:` IDLE branch — `n_frontier = 0; n_added = 0` — stays as the final fallback.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_node_content_address.py -k drift_arm -v`
Expected: PASS.

- [ ] **Step 5: Run the full node test file + back-compat**

Run: `python -m pytest tests/test_node.py tests/test_node_content_address.py -v`
Expected: PASS (existing node tests unchanged; `content_address=False` never builds a `DRIFT`-ranking state because `current=None`).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/node.py tests/test_node_content_address.py
git commit -m "feat(node): DRIFT arm — scheduler-driven drift_pass + reopen_drifted in tick"
```

---

## Task 5: End-to-end flywheel test

**Files:**
- Test: `tests/test_node_content_address.py`

This task adds NO production code — it proves the full loop with the machinery from Tasks 2–4. If it fails because the re-opened claim is not re-selected, that is an integration finding to surface (a `PENDING`+plan claim should be selectable; investigate the ledger/scheduler before changing the test).

- [ ] **Step 1: Write the flywheel test**

Append to `tests/test_node_content_address.py`:

```python
def test_flywheel_relicenses_against_moved_world(monkeypatch):
    r = methyl_node()
    for _ in range(3):
        r.tick()
    c = next(x for x in r.corpus.claims if x.id == "c-true")
    assert c.status == Status.LICENSED
    h_a = c.licensing.satisfactions[0].materialization.dimnames_hash
    assert h_a is not None

    import polymer_claims.materialization as mat_mod
    from polymer_claims.contracts import load_contract as real_load

    h_b = "sha256:" + "b" * 64
    assert h_b != h_a
    monkeypatch.setattr(
        mat_mod, "load_contract",
        lambda ref: real_load(ref).model_copy(update={"dimnames_hash": h_b}),
    )
    r.refresh_world()

    # drift tick -> reopen
    r.tick()
    c = next(x for x in r.corpus.claims if x.id == "c-true")
    assert c.status == Status.PENDING

    # re-license tick(s) -> records the NEW address H_B
    for _ in range(5):
        r.tick()
        c = next(x for x in r.corpus.claims if x.id == "c-true")
        if c.status == Status.LICENSED:
            break
    assert c.status == Status.LICENSED
    assert c.licensing.satisfactions[0].materialization.dimnames_hash == h_b

    # world is fresh again: another tick does NOT re-open it
    r.tick()
    c = next(x for x in r.corpus.claims if x.id == "c-true")
    assert c.status == Status.LICENSED
```

- [ ] **Step 2: Run the flywheel test**

Run: `python -m pytest tests/test_node_content_address.py -k flywheel -v`
Expected: PASS — recorded address tracks the world across re-open → re-license; no re-drift once fresh.

- [ ] **Step 3: Commit**

```bash
git add tests/test_node_content_address.py
git commit -m "test(node): end-to-end flywheel — world moves -> reopen -> re-license records new address"
```

---

## Task 6: Serve surface — `POST /refresh` + `/status` drift fields

**Files:**
- Modify: `src/polymer_claims/server.py`
- Test: `tests/test_server.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_server.py` (below the existing tests; reuses the module's `TestClient` import):

```python
def _methyl_client():
    from tests.conftest import methyl_node

    runner = methyl_node()
    app = create_app(runner, interval=3600, autostart=False)
    return TestClient(app), runner


def test_refresh_endpoint_and_status_drift(monkeypatch):
    client, runner = _methyl_client()
    with client:
        for _ in range(3):
            client.post("/step")  # license the claim (records the address)

        body = client.post("/refresh").json()
        assert body["current"]["dimnames_hash"] is not None
        assert body["n_reopened"] == 0
        assert body["last_drift"] is None

        # status carries the same drift fields
        status = client.get("/").json()
        assert status["n_reopened"] == 0

        # move the world, refresh, step -> drift re-opens the claim
        import polymer_claims.materialization as mat_mod
        from polymer_claims.contracts import load_contract as real_load

        monkeypatch.setattr(
            mat_mod, "load_contract",
            lambda ref: real_load(ref).model_copy(update={"dimnames_hash": "sha256:" + "b" * 64}),
        )
        client.post("/refresh")
        client.post("/step")  # DRIFT tick

        status = client.get("/").json()
        assert status["n_reopened"] == 1
        assert status["last_drift"]["drifted"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_server.py -k refresh -v`
Expected: FAIL — `POST /refresh` returns 404 (no route) / `KeyError: 'n_reopened'`.

- [ ] **Step 3: Implement the endpoint + status fields**

In `src/polymer_claims/server.py`, inside `create_app` (which closes over `runner` and `lock`):

(a) Add a `_drift_status()` helper next to `_status()`:

```python
    def _drift_status() -> dict:
        rec = runner.last_drift
        return {
            "n_reopened": runner.n_reopened,
            "last_drift": None if rec is None
            else {"examined": rec.examined, "drifted": len(rec.drifted)},
        }
```

(b) Merge the drift fields into `_status()` — change its return to:

```python
    def _status() -> dict:
        last = runner.frames[-1]
        return {
            "running": runner.running,
            "frame_index": runner.frame_index,
            "n_frames": len(runner.frames),
            "n_nodes": last.stats.n_nodes,
            "n_licensed": last.stats.n_licensed,
            **_drift_status(),
        }
```

(c) Add the route (place it near `/step`):

```python
    @app.post("/refresh")
    async def refresh() -> JSONResponse:
        async with lock:
            current = await asyncio.to_thread(runner.refresh_world)
        return JSONResponse(content={"current": _obj(current), **_drift_status()})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_server.py -k refresh -v`
Expected: PASS.

- [ ] **Step 5: Run the full server suite for back-compat**

Run: `python -m pytest tests/test_server.py -v`
Expected: PASS — existing tests unchanged; `/status` gains fields but the old keys are intact (`test_root_status` still passes).

- [ ] **Step 6: Commit**

```bash
git add src/polymer_claims/server.py tests/test_server.py
git commit -m "feat(serve): POST /refresh + n_reopened/last_drift on /status"
```

---

## Task 7: Full-suite green

**Files:** none (verification).

- [ ] **Step 1: Run the umbrella suite**

Run: `python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 2: Run check-all.sh**

Run: `./check-all.sh`
Expected: ALL GREEN (grammar/protocol/viewer untouched; umbrella additive).

- [ ] **Step 3: Commit any lint/format fixups (if check-all surfaced them)**

```bash
git add -A
git commit -m "chore(ces-4): lint/format fixups"
```

(Skip if nothing changed.)

---

## Self-Review (completed)

**Spec coverage:** §2 recording → Task 2; §3 refresh_world/cache-bust → Tasks 1+3; §4 scheduler `current` + DRIFT arm → Task 4; §5 `/refresh` + `/status` → Task 6; §6 tests (recording on/off, refresh, drift, flywheel, server) → Tasks 2–6. All spec sections map to a task.

**Type/name consistency:** `content_address`, `profiles`, `self.current`, `self.last_drift`, `self.n_reopened`, `refresh_world`, `clear_contract_cache`, `_drift_status` used identically across tasks. `materializations=` matches `execute_ground`/`run_cycle`. Monkeypatch target is `polymer_claims.materialization.load_contract` in every test (the bound-name fix).

**Placeholder scan:** none — every code step shows the actual code and the exact command + expected result.

**Risk flagged:** Task 5 (re-licensing a re-opened claim through the live scheduler) is the one integration unknown; the task notes it explicitly so the implementer investigates rather than weakens the test.
