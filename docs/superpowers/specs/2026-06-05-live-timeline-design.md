# Live Timeline — Design Spec

**Date:** 2026-06-05
**Status:** Approved (layout-stability fork resolved: warm-started / stable).
**Goal:** Make the claims-universe viewer *live* — play back the universe **evolving across `run_cycle`
iterations** (the north-star "buzzing universe"), with **stable, warm-started** node positions so existing
claims hold their place and only new structure perturbs locally (the precision-instrument register, not a
lava lamp). v1 is a **precomputed timeline file**; a live node-server polling endpoint is the follow-on.

Two parts: **(A)** engine emits a `TopologyTimeline` (one warm-started `TopologyExport` frame per cycle +
that cycle's stats); **(B)** the viewer animates across frames with a transport bar.

---

## Part A — Engine (protocol-only; grammar untouched; pure/deterministic)

### A1 — warm-started layout (`topology.py`)
Add an optional seed-position input so a frame can be laid out *continuing from* the previous frame:
- `export_topology(corpus, *, layout, seed_positions: dict[str, tuple[float,float,float]] | None = None)`.
- `_force_directed_layout(node_ids, edges, seed_positions=None)`: change the init from
  `pos = {nid: list(_seed_position(nid)) for nid in node_ids}` to
  `pos = {nid: list((seed_positions or {}).get(nid) or _seed_position(nid)) for nid in node_ids}`.
  Existing nodes start from their prior-frame position (FR perturbs them locally); brand-new nodes start
  from their id-hash seed and settle in. Same fixed iterations/cooling.
- `layout_id` records warm-start: `…,seed=sha256` → `…,seed=warm` when `seed_positions` is non-empty (so a
  frame is self-describing / reproducible).
- **Purity preserved:** seed positions are passed in (no clock/random/IO). Determinism: identical
  `(corpus, seed_positions)` → identical output. The existing no-seed behavior is byte-unchanged
  (default `None`).

### A2 — `export_timeline` + models (`topology.py` or a sibling `timeline.py`)
- `FrameStats` (frozen): per-cycle summary derived from the `CycleResult` — `cycle_index: int`,
  `n_nodes: int`, `n_licensed: int`, `n_pending: int`, `n_conjectured: int`, `n_rejected: int`,
  `n_edges: int`, `n_effective_edges: int`, `n_provisional_edges: int`, `n_frontier: int`,
  `n_added: int` (claims generated this cycle), `n_newly_licensed: int` (licensed delta vs prior frame).
- `TimelineFrame` (frozen): `topology: TopologyExport`, `stats: FrameStats`.
- `TopologyTimeline` (frozen): `frames: tuple[TimelineFrame, ...]`, `n_cycles: int`.
- `export_timeline(corpus, adapters, ctx, *, n_cycles, layout=Layout.FORCE_DIRECTED, ledger=None, …) ->
  TopologyTimeline`:
  - Frame 0: `export_topology(corpus, layout)` (no seed) + stats from the seed corpus (cycle_index 0,
    n_added 0).
  - For i in 1..n_cycles: `result = run_cycle(corpus, adapters, ctx, ledger=led, …)`; thread
    `corpus = result.corpus`, `led = result.ledger`; `frame = export_topology(corpus, layout,
    seed_positions=<prev frame's {id: position}>)`; `stats` derived from `result` (counts from the
    post-cycle corpus + `result.audit`/`result.generation`/`result.frontier`). Append.
  - Pure/deterministic given `(corpus, adapters, ctx, n_cycles, ledger)`; caller supplies adapters/ctx
    (same contract as `run_cycle`). No IO.
- Export the public names from `polymer_protocol/__init__.py`.

### A3 — CLI + sample
- `polymer-claims export-timeline <corpus.json> --cycles N [--out timeline.json]` in
  `src/polymer_claims/cli.py`: load the corpus, run `export_timeline` with the default reference adapters +
  ctx, write `timeline.model_dump_json()`.
- A `viewer/scripts/make_timeline.py` that builds a seed corpus that *grows + licenses over cycles* (so the
  playback visibly evolves — start mostly PENDING-with-plans + a couple proposers/injected so new nodes
  appear and statuses flip toward LICENSED across frames), runs `export_timeline`, writes
  `viewer/public/sample-timeline.json` (commit it). ≥8 frames, visible growth + licensing + ≥1
  representation-revision appearing.

---

## Part B — Viewer (timeline playback)

### B1 — data + store
- `src/lib/timeline.ts`: TS types for `TopologyTimeline`/`TimelineFrame`/`FrameStats` + a loader for
  `public/sample-timeline.json`.
- Store (`store.ts`) gains: `timeline`, `playing: bool`, `frame: number` (fractional during playback),
  `speed: number` (frames/sec), plus `play/pause/seek(frame)/setSpeed`. Selection/hover/filters unchanged.

### B2 — transport bar (`components/chrome/TransportBar.tsx`)
- Bottom-center, hairline-bordered, D2: **play/pause** button (electric blue), a **scrub slider** across
  frames, a mono **frame counter** `frame 03 / 12` (tabular-nums), a **speed** control (e.g. 0.5× / 1× /
  2×), and a `§` marker. Scrubbing seeks; play advances `frame` via a rAF/`useFrame` ticker (NO wall-clock
  in the engine — the viewer owns animation time, that's fine client-side).

### B3 — frame interpolation in the scene
- The scene consumes an **interpolated frame state** derived from `floor(frame)`→`ceil(frame)` at fraction
  `frame - floor(frame)`:
  - **Position:** lerp each node between its position in frame A and frame B (warm-start keeps these close,
    so motion is small/coherent). A node absent in A but present in B **enters** (scale 0→1 + fade in at
    its B position); present in A but absent in B **exits** (scale→0 + fade out).
  - **Status color:** crossfade a node's color between frames when its status changed (e.g. pending→licensed
    amber→blue) — a visible "licensing" moment.
  - **Edges:** appear/disappear with opacity fade; provisional/effective styling per the current frame.
- Reuse the existing `Nodes`/`Edges` components, fed the interpolated set instead of the static export.

### B4 — live readout
- `ReadoutOverlay` shows the **current frame's `FrameStats`** (cycle index, n_nodes, per-status counts,
  edges eff/prov, frontier, **+N added / +N newly licensed this cycle**) + the frame's `layout_id` (`warm`)
  — all tabular-nums. The static single-export path still works when no timeline is loaded.

---

## Determinism / purity / invariants
- Engine: pure/deterministic, no clock/random/IO; grammar untouched; Corpus stays 4 collections;
  `TopologyTimeline` is frozen + JSON round-trips. The warm-start default-None path leaves existing
  `export_topology` output byte-identical.
- Viewer: animation time is client-side (rAF) — never in the engine.

## Acceptance
- `export_timeline` over a growing seed corpus yields N+1 frames with monotone-ish licensing and **stable
  positions** (a node present in consecutive frames moves only a small bounded amount — assert the warm-start
  keeps Δposition small vs a from-scratch relayout). `TopologyTimeline` JSON round-trips. Full grammar +
  protocol suites green; ruff clean; isolation holds.
- `polymer-claims export-timeline` writes a valid timeline; the build+install smoke still passes.
- Viewer: `npm run dev` plays the sample timeline — press play and the universe **grows and licenses**
  smoothly (no node teleporting), the transport bar scrubs, the readout shows per-cycle stats. `npm run
  build` + `tsc` clean. Verified in-browser.

## Non-goals (this slice)
- A **live node-server endpoint** the viewer polls (real-time streaming from a running node) — the next step
  after precomputed playback proves out.
- Lasso/box-select, time-scrub gestures beyond the scrub bar, multi-timeline compare.
- Any `PolymerGenomicsAPI/` change; any publish.
