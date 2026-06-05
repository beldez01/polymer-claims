# Live Node Server — Design Spec

**Date:** 2026-06-05
**Status:** Approved direction (written pre-compaction; build after). Baked-in defaults flagged below.
**Goal:** Make the viewer stream from a **running node in real time** — replacing the precomputed
`sample-timeline.json` with a live feed of frames as the engine actually advances. This is the "agents
elaborating live" step of the platform vision ([[polymer-claims-platform-vision-north-star]]): a process
runs the engine loop, broadcasts each new `TopologyExport` frame, and the viewer's **live mode** plays them
as they arrive.

Builds directly on what's merged: `export_timeline` / warm-started `export_topology` (engine) + the viewer's
timeline store + transport bar + `interpolateFrame` playback. Live mode **reuses the playback machinery** —
frames just arrive over time instead of from a file.

---

## Baked-in decisions (forks resolved with defaults; adjust at build time if desired)

- **Transport: SSE (Server-Sent Events).** One-directional server→client is exactly our need; plain HTTP;
  `EventSource` auto-reconnects. (Not WebSocket — bidirectional complexity we don't need; client control is
  separate POST endpoints.)
- **Server framework: FastAPI + uvicorn + SSE**, shipped as an **optional extra** `polymer-claims[serve]`
  (keeps the core wheel lean; matches the broader Polymer stack which is FastAPI). SSE via starlette's
  `EventSourceResponse` (sse-starlette) or a manual `StreamingResponse` with `text/event-stream`.
- **Loop driver: the #5d `next_action` scheduler.** The node ticks `next_action(state, budget, config)`,
  executes the recommended action (RUN_CYCLE or a daemon pass), and broadcasts the resulting frame — the
  most on-vision "what should the node do next" behavior, reusing built machinery.
- **Engine stays pure; the SERVER owns the clock/loop** (the impure driver). The runner passes all time-like
  things into the pure engine — consistent with the standing purity rule.

---

## Part A — the node server (`polymer-claims serve`)

### A1 — `NodeRunner` (`src/polymer_claims/node.py`)
A plain object holding live mutable state (this is the impure driver layer, NOT the pure engine):
- fields: `corpus`, `ledger`, `adapters`, `ctx`, `config` (SchedulerConfig), `budget`, `frames: list[TimelineFrame]`, `frame_index`, `prev_positions: dict[str,pos]`, `running: bool`.
- `tick() -> TimelineFrame`: compute `state = SchedulerState(corpus, ledger, current=ctx-ish, …)`; `action = next_action(state, budget=…, config=…)`; if `RUN_CYCLE` → `result = run_cycle(corpus, adapters, ctx, ledger=ledger, …)` and thread corpus+ledger; if a daemon action and its inputs are available → run that daemon pass; if `None` → no-op (idle). Then `frame = export_topology(corpus, FORCE_DIRECTED, seed_positions=prev_positions)` + `FrameStats` (same derivation as `export_timeline`); update `prev_positions`; append; return the frame.
- `snapshot() -> TopologyTimeline`: the accumulated frames (for late-joiners to catch up).
- Pure-engine calls only; the runner owns the loop/wall-clock.

### A2 — the FastAPI app + SSE (`src/polymer_claims/server.py`)
- `create_app(runner, *, interval) -> FastAPI` with CORS allowing `localhost:3000` (+ configurable origins).
- A background async task: every `interval` seconds, `runner.tick()` and publish the new frame to an
  `asyncio` broadcast (an async queue / `anyio` broadcast) that SSE subscribers read from. Pause when
  `runner.running` is False.
- Endpoints:
  - `GET /` → node status `{running, frame_index, n_frames, n_nodes, n_licensed}`.
  - `GET /state` → the current frame `{topology, stats, frame_index}`.
  - `GET /timeline` → the full accumulated `TopologyTimeline` (late-joiner catch-up).
  - `GET /stream` → **SSE**: on connect, send the current frame, then one `event: frame` per tick with
    `data: <TimelineFrame JSON>`. Auto-flush; heartbeat comment every ~15s to keep proxies open.
  - `POST /pause` / `POST /resume` / `POST /step` → toggle/advance the loop (control).
- All JSON via the existing frozen models' `model_dump_json`.

### A3 — CLI `serve` (`src/polymer_claims/cli.py`)
- `polymer-claims serve [--seed-corpus PATH] [--port 8000] [--interval 1.5] [--budget N] [--max-frames N] [--origins ...]`:
  load the seed corpus (or a small built-in default), build a `NodeRunner` with the default reference
  adapters + ctx + `SchedulerConfig()`, `uvicorn.run(create_app(runner, interval=…), port=…)`. Import the
  `serve` deps lazily inside the handler so the core CLI works without the `[serve]` extra installed (print
  a helpful "pip install polymer-claims[serve]" message if missing).
- Add the optional dependency group to the umbrella `pyproject.toml`:
  `[project.optional-dependencies] serve = ["fastapi>=0.110", "uvicorn>=0.27", "sse-starlette>=2"]`.

---

## Part B — viewer live mode

### B1 — live client + store (`viewer/src/lib/live.ts`, `store.ts`)
- `connectLive(url, { onFrame, onStatus })`: `fetch(url + '/timeline')` to seed accumulated frames, then open
  `new EventSource(url + '/stream')`; on each `frame` event, parse the `TimelineFrame` and call `onFrame`.
  Expose `disconnect()`. EventSource auto-reconnects on drop.
- Store gains: `liveUrl`, `connected: bool`, `following: bool` (auto-advance to newest), `connectLive/disconnectLive`,
  and a `pushFrame(frame)` that appends to `timeline.frames` and, if `following`, sets `frame` to the last
  index. Reuses the existing `timeline`/`frame`/`playing` machinery.

### B2 — connection UI + live indicator
- A small **connect control** (in the header or transport bar, D2 hairline): a URL input (default
  `http://localhost:8000`), Connect/Disconnect, and a **● LIVE** indicator — a small electric-blue dot
  (steady when following, hollow when scrubbed back; NO glow — a 1px ring pulse at most). Mono status text
  (`live · frame NN` / `disconnected`), tabular-nums.
- **Jump-to-live** button (appears when scrubbed back off the newest frame) → sets `following=true` + seeks
  to last. Scrubbing back through accumulated frames still works (it just stops "following").
- Mode is implicit: file mode (load `sample-timeline.json`, current default) vs live mode (connected). A
  toggle/segmented control in the transport bar switches between them.

### B3 — playback reuse
- The scene + interpolation are unchanged: incoming live frames append to `timeline.frames`; `interpolateFrame`
  + `TimelineDriver` already animate between frames. When following live, the driver advances toward the
  newest frame; when a new frame arrives mid-interpolation it extends smoothly (warm-start keeps positions
  stable, so live growth glides in).

---

## Determinism / purity / invariants
- Engine pure/deterministic, untouched; grammar untouched; Corpus at 4. The `NodeRunner` + server are the
  impure driver (own the clock/loop/network) — they live in the umbrella `polymer_claims` package, never in
  `grammar`/`protocol`.
- The `[serve]` extra is optional: the core wheel + existing CLI commands work without it; the
  build/test-install smoke runs without installing `[serve]`.

## Acceptance
- `polymer-claims serve --seed-corpus <sample> --interval 1.5` starts a node; `GET /state` returns the
  current frame; `GET /stream` emits a frame per tick (verify with a TestClient / curl reading the SSE
  stream); `GET /timeline` returns the accumulated `TopologyTimeline`; `/pause`+`/resume` work.
- Viewer live mode: enter the URL → Connect → **● LIVE**, and the universe **updates in real time** as the
  node ticks (new nodes + licensing appear with no reload); scrub-back works; jump-to-live works; survives a
  server restart (EventSource reconnects).
- Server tests (FastAPI TestClient) green; engine + viewer suites unaffected; `tsc`+`build` clean; the
  install smoke passes WITHOUT `[serve]`.

## Non-goals (this slice)
- **Deploy-an-agent UX** (injecting custom adapters/agents at runtime; the BYO-compute/federated layer) —
  v1 runs the built-in reference adapters + scheduler. A `POST /inject` claim endpoint is a noted future
  hook, not built here.
- Auth, multi-tenant, persistence (in-memory; restart = fresh node), and any actual deployment (local only;
  no publish — consistent with the standing posture).
- Any `PolymerGenomicsAPI/` change.
