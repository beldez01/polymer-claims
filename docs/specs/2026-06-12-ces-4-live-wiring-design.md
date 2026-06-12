# CES-4 — live wiring: record content-addresses + run the drift daemon

**Status:** Design / phase spec. v0.1
**Date:** 2026-06-12
**Author:** Z. Belden
**Depends on:** CES-3 (`materialization_map`, the `run_cycle(materializations=)` seam, the tightened
`drift._is_fresh`), CES-1 (`load_contract` → `dimnames_hash`), CES-0 (`MaterializationContext`
content-address fields, `content_hash`, `profile_oracle_id`), #5a (`drift_pass`/`reopen_drifted`),
#5d (`next_action`/`ActionKind.DRIFT`/`SchedulerState`). Slice CES-4 of the CES decomposition — the
**running-node** leg: it makes the fully-pinned license (CES-3) and the drift daemon (#5a) act in the
live `NodeRunner`/`serve` loop instead of only in tests.

**Decided this session:** wire **both halves** (record + drift daemon); derive the current-world
context by **recompute-from-disk** (a `refresh_world()` that busts `load_contract`'s cache and
recomputes via `materialization_map`); ship a **minimal serve surface** (`POST /refresh` + drift
fields on `/status`). Feature is **opt-in** (`content_address=False` default) so every existing node /
server test stays byte-identical. Grammar and protocol are **untouched**.

---

## 0. Goal

Today the live driver records nothing of the content-address and never drifts:

- `NodeRunner.tick` (`src/polymer_claims/node.py:127`) calls `run_cycle(...)` **without**
  `materializations=`, so a license minted by the running node carries only the shared cycle `ctx`
  (`api_version`/`data_version`) — not the `dimnames_hash`/`profile_hash`/`semantic_run_id` that
  CES-3 made recordable.
- `tick` builds `SchedulerState(...)` **without** `current=`, so the scheduler's `DRIFT` branch
  (`economics.py:117`, which needs `state.current`) can never fire; and `tick` only handles
  `ActionKind.RUN_CYCLE` — a `DRIFT` recommendation would fall through to an IDLE heartbeat tick.

CES-4 closes both:

1. **Record** — the running node passes `materialization_map(corpus, ctx)` into `run_cycle`, so a
   live license records its full content-address (the CES-3 deliverable, now live).
2. **Drift on it** — the node holds a `current`-world context (recomputed from disk); the scheduler
   ranks a `DRIFT` action when a licensed claim's content-address no longer matches the current
   world; `tick` executes `drift_pass` + `reopen_drifted`, re-opening the stale claim to
   `PENDING(MATERIALIZATION_DRIFTED)` so the next cycle re-licenses it against the new world. The
   flywheel closes.

This is the deferred item named at the end of the CES-3 spec (§7: "live `serve`/`NodeRunner`
wiring of the map").

---

## 1. Architecture & boundaries

- **Umbrella-only.** All new logic lives in `src/polymer_claims/node.py`,
  `src/polymer_claims/server.py`, and a one-function addition to
  `src/polymer_claims/contracts/__init__.py` (`clear_contract_cache`), reusing the existing umbrella
  `materialization_map` (`src/polymer_claims/materialization.py`) and the existing **pure** protocol
  entry points (`run_cycle(materializations=)`, `drift_pass`, `reopen_drifted`, `next_action`).
  **Grammar and protocol packages are untouched.** Corpus stays 4.
- **Purity preserved.** Every value the node derives still comes from a pure engine call; the only
  new impurity is `materialization_map`'s bundled-contract read (the established CES-1/CES-2/CES-3
  boundary) and the `load_contract.cache_clear()` in `refresh_world`. No clock, no randomness.
- **Opt-in.** A constructor flag `content_address: bool = False` gates the whole feature. Default
  `False` → today's behavior exactly (no map passed, no `current` on the scheduler state, no `DRIFT`
  arm reachable). Every existing node/server test stays byte-identical by construction.

---

## 2. The recording half (`NodeRunner.tick`)

When `content_address` is on, recompute the per-claim map immediately before the `RUN_CYCLE` call and
thread it into `run_cycle`:

```python
mats = materialization_map(self.corpus, self.ctx, profiles=self.profiles) if self.content_address else None
result = run_cycle(
    self.corpus, self.adapters, self.ctx,
    ledger=self.ledger, materializations=mats, **self.run_cycle_kwargs,
)
```

- The map is recomputed **each** `RUN_CYCLE` tick because the corpus changes between ticks (new
  claims, re-opened claims). It resolves each content-addressed claim's `DataHandle.ref` via
  `load_contract` and the canonical profile (CES-3 §2).
- An **empty** map (`{}` — corpus has no content-addressed claims) is falsy, so `execute_ground`'s
  `materializations.get(c.id, ctx) if materializations else ctx` falls back to the shared `ctx`: the
  recording half is a **no-op** unless the corpus actually has content-addressed claims. This is what
  keeps the default-off path and content-address-free corpora byte-identical.
- `materializations` is passed **explicitly**, not via `run_cycle_kwargs` (callers never set it).

`materialization_map` imports no numpy, so `node.py` stays numpy-free (base `import polymer_claims`
unaffected).

---

## 3. The current-world context (`refresh_world`)

The node holds `self.current: MaterializationContext`. `refresh_world()` recomputes it from disk:

```python
def refresh_world(self) -> MaterializationContext:
    """Re-read the live SE-Contracts/profile and recompute the current-world content-address.
    Operator/endpoint-triggered (not per-tick): busts the contract cache so a re-published
    dataset is actually re-read, then takes the v1 single-world representative."""
    clear_contract_cache()
    m = materialization_map(self.corpus, self.ctx, profiles=self.profiles)
    self.current = next(iter(m.values()), self.ctx)
    return self.current
```

- **Cache-bust.** The lru-cache lives on the private `_load_contract(uid)`
  (`contracts/__init__.py:64`), not on the public `load_contract` wrapper, so the node cannot call
  `load_contract.cache_clear()`. CES-4 adds a one-line public helper to `contracts/__init__.py`:
  ```python
  def clear_contract_cache() -> None:
      """Drop the bundled-contract lru-cache so the next load_contract re-reads disk (a node
      refresh after a dataset is re-published)."""
      _load_contract.cache_clear()
  ```
  exported from the package and called by `refresh_world`. Without it the recompute would return the
  address cached at license time and drift could never be observed.
- **Single-world representative (v1).** All content-addressed claims in the live demo corpus share
  one dataset + the canonical profile, so every map entry carries the same
  `dimnames_hash`/`profile_hash`; `next(iter(m.values()))` is an exact representative. Empty map →
  fall back to `self.ctx` (no content-address fields → drift never fires on them → back-compat).
- **Critical invariant — unchanged disk ⟹ no drift.** Because both the recorded materialization (at
  license time) and `self.current` (at refresh time) come from the **same** `materialization_map`
  recipe over the **same** contracts, an unchanged disk yields identical addresses, so
  `drift._is_fresh` returns true and nothing spuriously re-opens. Drift fires **only** when a
  contract's `dimnames_hash` (the SE-Contract content-address — the feature/sample set) or the
  profile's `profile_hash` actually moves.
- **Trigger model.** `refresh_world` is operator/endpoint-triggered (via `POST /refresh` or a direct
  call), not run every tick — a per-tick recompute would both be wasteful and, against the lru-cache,
  see nothing change. A refresh is the explicit "re-survey the world" action.

`self.current` is initialized in `__init__`: `refresh_world()` when `content_address` is on, else the
seed `ctx` (drift inert).

---

## 4. The drift half (scheduler + `tick`)

- **Scheduler sees the world.** When `content_address` is on, `tick` builds
  `SchedulerState(corpus=..., ledger=..., proposers_available=..., current=self.current)`. The
  scheduler's existing `DRIFT` branch (`economics.py:117–128`) then ranks a `DRIFT` action whose
  value is `w.drift * n_drifted`, where `n_drifted` is the count of LICENSED claims that
  `_is_fresh` rejects against `self.current` — so it never recommends a no-op pass.
- **`tick` gains a `DRIFT` arm:**

```python
elif action is not None and action.kind == ActionKind.DRIFT:
    _, record = drift_pass(self.corpus, current=self.current)
    self.corpus = reopen_drifted(self.corpus, record)   # re-executable findings -> PENDING
    self.last_drift = record
    self.n_reopened += len(record.drifted)
    n_frontier = 0
    n_added = 0
```

  Then the shared tail (export topology with warm-start, `frame_stats`, append/trim frame) runs as
  for any tick — so a `DRIFT` tick still emits a heartbeat frame, and the re-opened claim shows up as
  no-longer-licensed in the next topology.
- **Flywheel alternation.** On a single-claim corpus: once the claim is `LICENSED` it is not
  selectable, so `RUN_CYCLE` has no productive candidate and `DRIFT` (if `n_drifted>0`) fires; after
  `reopen_drifted` the claim is `PENDING`, so `n_drifted` drops to 0 (no `DRIFT` candidate) and
  `RUN_CYCLE` re-licenses it — recording the **new** address from the now-current map. No scheduler
  weights change; this is the existing economics (§5d) acting on a populated `current`.
- **New runner state:** `self.current`, `self.last_drift: DriftRecord | None = None`,
  `self.n_reopened: int = 0`. None touch the protocol.

---

## 5. The serve surface (`server.py`)

- **`POST /refresh`** — recompute the current world off the event loop, under the tick-lock:

```python
@app.post("/refresh")
async def refresh() -> JSONResponse:
    async with lock:
        current = await asyncio.to_thread(runner.refresh_world)
    return JSONResponse(content={"current": _obj(current), **_drift_status()})
```

  Running under `lock` (the same lock that serializes `tick`) keeps `refresh_world`'s corpus read
  consistent with concurrent ticks; `to_thread` keeps the loop free during the bundled-file read.
- **`/status`** (the `_status()` helper feeding `/`, `/pause`, `/resume`) gains drift fields:
  `n_reopened` (running total) and `last_drift` (a small summary: `examined`, `drifted` count, or
  `None`). A `_drift_status()` helper builds them so `/refresh` and `/status` agree.
- **No protocol change.** `TimelineFrame`/`frame_stats` stay untouched (purity); per-frame drift
  annotation for the viewer is a noted small follow-up (§7).
- **Guard:** `/refresh` on a `content_address=False` runner is harmless — `refresh_world` recomputes
  an empty map → `self.current = self.ctx`, `n_drifted` stays 0. (It is still exposed; the endpoint
  does not assume the feature is on.)

---

## 6. Tests

**Simulating a re-published dataset.** Tests move the dataset's content-address by monkeypatching
`polymer_claims.materialization.load_contract` (the name `materialization_map` actually calls —
`materialization.py` binds `load_contract` into its own namespace at import, so patching
`polymer_claims.contracts.load_contract` would NOT take effect) to return an `SEContractRef` whose
`dimnames_hash` is `H_B`. This stands in for the SE-Contract being re-published with a different
feature/sample set; no committed fixture is mutated.

**Umbrella node** (`tests/`):
- **Recording on:** a content-addressed single-claim corpus run through `NodeRunner(content_address=True)`
  ticks to `LICENSED`; the licensed claim's `Satisfaction.materialization` now carries
  `dimnames_hash`/`profile_hash`/`semantic_run_id` (all set, == the `materialization_map` recipe).
- **Recording off (back-compat):** the same corpus with `content_address=False` mints a license whose
  materialization has those fields `None` — byte-identical to pre-CES-4.
- **`refresh_world`:** with `load_contract` monkeypatched to return a contract whose `dimnames_hash`
  is `H_B` (≠ the licensed `H_A`, simulating a re-published dataset), `refresh_world()` sets
  `self.current.dimnames_hash == H_B`; unchanged disk leaves it == `H_A` (no drift).
- **Drift arm:** starting from a `LICENSED` claim recorded under `H_A`, after `refresh_world` moves
  `self.current` to `H_B`, the next `tick` recommends `DRIFT` and re-opens the claim to
  `PENDING` with `pending_reason == MATERIALIZATION_DRIFTED`; `runner.n_reopened == 1`,
  `runner.last_drift.drifted` names the claim.
- **End-to-end flywheel (the deliverable):** seed → tick to `LICENSED` (records `H_A`) → monkeypatch
  the dataset to `H_B` → `refresh_world()` → tick fires `DRIFT` → claim re-opens → next tick
  `RUN_CYCLE` re-licenses, now recording `H_B` → a final `refresh_world()` shows the claim fresh
  again (no further drift). Asserts the recorded address tracked the world across the full loop.

**Server** (`tests/`, the `[serve]` path):
- `POST /refresh` returns the new `current` context and `n_reopened`; after a simulated dataset move
  it reflects the moved address.
- `/status` (`GET /`) exposes `n_reopened` and a `last_drift` summary.

**Determinism / back-compat:**
- Every existing `node`/`server` test stays green unchanged (default `content_address=False`).
- `check-all.sh` ALL GREEN (grammar/viewer/protocol untouched; umbrella additive).

---

## 7. Scope fences & honesty

- **v1 single-world.** `self.current` is one representative content-address; the live demo corpus
  shares one dataset + the canonical profile. A corpus whose claims address **different** datasets
  would need per-claim drift (call `drift` per distinct world); that is a documented **defer**,
  consistent with CES-3's one-profile scope. The recording half is already per-claim correct (it uses
  the full map); only the drift `current` is collapsed to a representative.
- **Opt-in, additive, protocol untouched.** One constructor flag, three runner fields, one `tick`
  arm, one endpoint, two `/status` fields. No grammar/protocol edits; Corpus stays 4.
- **Drift is exogenous and observed, not fabricated.** The node only re-opens a claim when a
  `refresh_world` recompute *from disk* shows the content-address actually moved. It cannot invent
  drift; an unchanged world never re-opens anything.
- **Synthetic-data caveat carries forward** (CES-2/CES-3): the content-address is real and complete,
  but it addresses synthetic betas until the real-public-data swap. Drift here is exercised by a
  monkeypatched `load_contract` standing in for a re-published dataset.
- **`semantic_run_id` is the Python-side composite** (CES-3 §6); validated Python/R hash parity is
  still deferred to its golden-fixture slice.

---

## 8. What CES-4 delivers vs defers

**Delivers:** live recording (`materialization_map` → `run_cycle` in `tick`); the `current`-world
context via `refresh_world` (recompute-from-disk, cache-busting); the scheduler-driven `DRIFT` arm in
`tick` (`drift_pass` + `reopen_drifted`); the `POST /refresh` endpoint + `n_reopened`/`last_drift` on
`/status`; the unit + server + end-to-end flywheel tests.

**Defers:** per-claim/multi-dataset drift (single-world v1); per-frame drift annotation in
`TimelineFrame` for the viewer (keeps protocol pure this slice); validated Python/R hash parity; the
real-public-data swap (CES-2 caveat). None block CES-4.

---

## 9. Invariants preserved

- **Grammar untouched; protocol purity intact** — all new logic is umbrella-side; the node still
  derives every value from a pure engine call. Determinism preserved.
- **Back-compat** — `content_address=False` (default) and the empty-map / fields-absent fallbacks
  keep every existing test byte-identical; only an opted-in, content-addressed corpus gains the new
  behavior.
- **Flywheel completeness** — a license now records the full content-address **as it is minted live**,
  and the running node re-opens it when the data/apparatus content-address moves, so the corpus
  self-heals toward the current world instead of silently holding a stale license.
