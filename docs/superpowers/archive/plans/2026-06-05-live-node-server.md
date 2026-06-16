# Live Node Server — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.
> Written pre-compaction — resume here for the "make it truly live" step.

**Goal:** A `polymer-claims serve` node that auto-advances the engine and streams `TopologyExport` frames over SSE; the viewer's live mode subscribes and plays them in real time.

**Spec:** `docs/superpowers/specs/2026-06-05-live-node-server-design.md` (binding; baked-in decisions: SSE, FastAPI `[serve]` extra, `next_action`-driven loop, engine stays pure / server is the impure driver).

**Builds on (already merged):** `export_timeline`/warm-started `export_topology`, `next_action` scheduler, viewer timeline store + transport bar + `interpolateFrame`.

**Verify:** root CLI/server tests `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/ -q`; engine unaffected `cd protocol && uv run pytest -q`; viewer `cd viewer && npx tsc --noEmit && npm run build`. ABSOLUTE paths (Bash cwd persists). Local-only, no push/publish.

---

## Branch A — `feat/live-node-server` (the server)

### Task 1: `NodeRunner` (pure-engine driver, no web yet)

**Files:** `src/polymer_claims/node.py`; Test `tests/test_node.py`.

- [ ] **Step 1 — failing test:** a runner over a growing seed corpus ticks N times and accumulates frames; licensing rises; positions warm-start-stable across ticks; `snapshot()` is a valid `TopologyTimeline`.
```python
def test_node_runner_ticks_and_accumulates():
    r = NodeRunner.from_seed(seed_corpus)          # default reference adapters + ctx + SchedulerConfig
    for _ in range(5): r.tick()
    tl = r.snapshot()
    assert len(tl.frames) >= 5
    assert tl.frames[-1].stats.n_licensed >= tl.frames[0].stats.n_licensed
    # warm-start stability between consecutive frames (reuse the export_timeline assertion)
```
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement** `NodeRunner` per spec §A1: `from_seed(corpus, *, adapters=…, ctx=…, config=SchedulerConfig(), budget=…)`; `tick()` = `next_action` → execute (RUN_CYCLE via `run_cycle` threading corpus+ledger; daemon passes only if inputs available; None → idle no-op frame) → warm-started `export_topology` + `FrameStats` (reuse the derivation from `timeline.py` — factor a shared `_frame_stats(...)` helper if clean) → append. Frame 0 = the seed snapshot. Pure-engine calls only.
- [ ] **Step 4 — green** (root tests + `protocol` unaffected + ruff).
- [ ] **Step 5 — commit** `feat(node): NodeRunner — scheduler-driven engine loop`.

### Task 2: FastAPI app + SSE + the `[serve]` extra

**Files:** `src/polymer_claims/server.py`; `pyproject.toml` (optional-deps); Test `tests/test_server.py` (skip if `[serve]` not installed).

- [ ] **Step 1 — failing test** (FastAPI `TestClient`): `GET /state` returns a frame; `POST /step` advances; `GET /timeline` returns accumulated frames; `GET /` returns status. (SSE stream test: read a couple events via the TestClient streaming context, or assert the broadcast helper emits.)
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement** `create_app(runner, *, interval, origins)` per spec §A2: CORS, the background tick task (every `interval`s while `running`, `runner.tick()` → publish to an asyncio broadcast), and endpoints `/`, `/state`, `/timeline`, `/stream` (SSE: current frame then `event: frame` per tick + ~15s heartbeat), `/pause`, `/resume`, `/step`. JSON via `model_dump_json`. Add `[project.optional-dependencies] serve = ["fastapi>=0.110","uvicorn>=0.27","sse-starlette>=2"]` to the umbrella `pyproject.toml`. Guard imports so the module only needs the extra when used.
- [ ] **Step 4 — green** (server tests pass with `[serve]` installed in the root env — add it to the dev group so tests run; the shipped wheel keeps it optional).
- [ ] **Step 5 — commit** `feat(server): FastAPI node server + SSE stream + serve extra`.

### Task 3: CLI `serve` + smoke

**Files:** `src/polymer_claims/cli.py`; Test `tests/test_cli.py`.

- [ ] **Step 1 — failing test:** `main(["serve", "--help"])` exits 0 and the command is registered; with `[serve]` missing, invoking `serve` prints the install hint and exits non-zero (simulate by monkeypatching the import).
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement** the `serve` subcommand per spec §A3 (lazy-import the server deps; build the runner from `--seed-corpus`/defaults; `uvicorn.run`). Keep `version`/`validate`/`run-cycle`/`loop`/`export-topology`/`export-timeline` unchanged.
- [ ] **Step 4 — green** + the existing `scripts/build_and_test_install.sh` still passes WITHOUT `[serve]` (the core CLI must import cleanly without it).
- [ ] **Step 5 — commit** `feat(cli): serve command (lazy serve extra)`.

**After 1–3 reviewed:** finish Branch A (merge local no-ff, no push). Manual check: `pip install -e '.[serve]'` (or uv) then `polymer-claims serve --interval 1` → `curl localhost:8000/state` + `curl -N localhost:8000/stream` shows frames ticking.

---

## Branch B — `feat/live-node-viewer` (viewer live mode)

> After A merged. Reuses the existing timeline playback.

### Task 4: live client + store

**Files:** `viewer/src/lib/live.ts`, `viewer/src/store.ts`.

- [ ] **Step 1:** `live.ts` — `connectLive(url, {onFrame, onStatus})`: GET `${url}/timeline` to seed frames, then `EventSource(${url}/stream)`; parse each `frame` event → `onFrame(TimelineFrame)`; `disconnect()`. Types reuse `viewer/src/lib/timeline.ts`.
- [ ] **Step 2:** store gains `liveUrl`, `connected`, `following`, `connectLive(url)`, `disconnectLive()`, `pushFrame(frame)` (append to `timeline.frames`; if `following`, seek to last). Keep the file path working.
- [ ] **Step 3:** `npx tsc --noEmit` clean. Commit `feat(viewer): live SSE client + store`.

### Task 5: connection UI + live indicator + jump-to-live

**Files:** `viewer/src/components/chrome/TransportBar.tsx` (or a new `LiveControl.tsx`); modify `ReadoutOverlay.tsx`/`Header.tsx`.

- [ ] **Step 1:** a D2 connect control — URL input (default `http://localhost:8000`), Connect/Disconnect, a **● LIVE** dot (electric blue, steady when following / hollow when scrubbed back, NO glow), mono status (`live · frame NN` / `disconnected`, tabular-nums). A file↔live segmented toggle.
- [ ] **Step 2:** **jump-to-live** button (shown when scrubbed off the newest frame) → `following=true` + seek to last. Scrubbing back stops following (still works on accumulated frames).
- [ ] **Step 3:** wire it so a running `polymer-claims serve` node drives the universe live (new nodes + licensing appear with no reload, gliding via warm-start). Reconnect on drop (EventSource default).
- [ ] **Step 4:** `npx tsc --noEmit` + `npm run build` clean; verify in-browser against a live `serve` node (or describe if no browser). Commit `feat(viewer): live mode — connect, LIVE indicator, jump-to-live`.

**After 4–5 reviewed:** finish Branch B (merge local no-ff, no push).

## Self-Review
- Spec coverage: NodeRunner (T1), server+SSE+extra (T2), CLI serve (T3), live client+store (T4), UI+indicator (T5). ✓
- Purity/isolation: NodeRunner+server live in the umbrella `polymer_claims` only; grammar/protocol untouched; `[serve]` optional; engine pure. ✓
- No placeholders: endpoint list, runner tick logic, store actions, UI elements all concrete. ✓
- Reuse: leans on `export_topology` warm-start + `FrameStats` + `next_action` + the viewer's `interpolateFrame`/`TimelineDriver` (no new playback engine). ✓
