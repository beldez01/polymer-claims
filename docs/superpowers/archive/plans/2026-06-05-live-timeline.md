# Live Timeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Engine emits a warm-started `TopologyTimeline` across `run_cycle` iterations; the viewer plays it back.

**Spec:** `docs/superpowers/specs/2026-06-05-live-timeline-design.md` (binding). Two branches: A (protocol + CLI), B (viewer).

**Verify:** protocol `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest -q && uv run ruff check src tests`; grammar isolation `cd ../grammar && uv run pytest tests/test_isolation.py -q`; viewer `cd ../viewer && npx tsc --noEmit && npm run build`. ABSOLUTE paths.

---

## Branch A — `feat/live-timeline-engine`

> `cd /Users/zbb2/Desktop/polymer-claims && git checkout -b feat/live-timeline-engine`

### Task 1: warm-started layout (`topology.py`)

**Files:** Modify `protocol/src/polymer_protocol/topology.py`; Test `protocol/tests/test_topology.py`.

- [ ] **Step 1 — failing test:** with `seed_positions` supplied for existing nodes, those nodes' output positions are within a small bound of their seeds (and a no-seed call is byte-identical to before):
```python
def test_warm_start_keeps_existing_nodes_near_seed():
    base = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
    seed = {n.id: n.position for n in base.nodes}
    warm = export_topology(corpus, layout=Layout.FORCE_DIRECTED, seed_positions=seed)
    for n in warm.nodes:
        dx = sum((a-b)**2 for a,b in zip(n.position, seed[n.id])) ** 0.5
        assert dx < 0.75                      # bounded drift, not a re-shuffle
    assert "seed=warm" in warm.layout_id

def test_no_seed_is_unchanged():
    a = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
    b = export_topology(corpus, layout=Layout.FORCE_DIRECTED, seed_positions=None)
    assert a == b
```
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement:** add `seed_positions: dict[str, tuple[float,float,float]] | None = None` to `export_topology` and thread into `_force_directed_layout`; init `pos = {nid: list((seed_positions or {}).get(nid) or _seed_position(nid)) for nid in node_ids}`; set `layout_id` suffix `seed=warm` when `seed_positions` is non-empty, else `seed=sha256`. Round positions as before.
- [ ] **Step 4 — green** + full protocol suite + ruff + isolation.
- [ ] **Step 5 — commit** `feat(protocol): warm-started export_topology (seed_positions)`.

### Task 2: `export_timeline` + timeline models

**Files:** Add to `protocol/src/polymer_protocol/topology.py` (or new `timeline.py`); export from `__init__.py`; Test `protocol/tests/test_timeline.py`.

- [ ] **Step 1 — failing test:**
```python
def test_timeline_grows_and_licenses_with_stable_positions():
    tl = export_timeline(seed_corpus, adapters, ctx, n_cycles=4)
    assert tl.n_cycles == 4 and len(tl.frames) == 5
    # licensing rises across frames
    lic = [f.stats.n_licensed for f in tl.frames]
    assert lic[-1] >= lic[0]
    # warm-started: a node present in consecutive frames moves only a little
    for a, b in zip(tl.frames, tl.frames[1:]):
        pa = {n.id: n.position for n in a.topology.nodes}
        for n in b.topology.nodes:
            if n.id in pa:
                d = sum((x-y)**2 for x,y in zip(n.position, pa[n.id]))**0.5
                assert d < 0.75
    # frame 1+ layout is warm
    assert "seed=warm" in tl.frames[1].topology.layout_id

def test_timeline_json_roundtrips():
    tl = export_timeline(seed_corpus, adapters, ctx, n_cycles=2)
    assert TopologyTimeline.model_validate_json(tl.model_dump_json()) == tl
```
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement** `FrameStats`, `TimelineFrame`, `TopologyTimeline` (frozen `_Model`s, per spec A2) + `export_timeline(corpus, adapters, ctx, *, n_cycles, layout=Layout.FORCE_DIRECTED, ledger=None)`:
  - frame 0 = `export_topology(corpus, layout)` + stats from the seed corpus (cycle_index 0, n_added 0, n_newly_licensed 0);
  - each subsequent: `result = run_cycle(corpus, adapters, ctx, ledger=led)`; thread corpus+ledger; `export_topology(corpus, layout, seed_positions={n.id:n.position for n in prev.topology.nodes})`; derive `FrameStats` from `result` (status counts from `result.corpus`; n_edges/effective/provisional from the new topology; n_frontier=len(result.frontier); n_added=len(result.generation.admitted); n_newly_licensed = licensed_now − licensed_prev).
  - Pure/deterministic; no IO. Import `run_cycle` (already in protocol).
- [ ] **Step 4 — green** + full protocol suite + ruff + isolation.
- [ ] **Step 5 — commit** `feat(protocol): export_timeline -> warm-started TopologyTimeline`.

### Task 3: CLI `export-timeline` + sample generator

**Files:** Modify `src/polymer_claims/cli.py`; add `viewer/scripts/make_timeline.py`; generate `viewer/public/sample-timeline.json`; Test `tests/test_cli.py`.

- [ ] **Step 1 — failing CLI test:** `main(["export-timeline", <corpus.json>, "--cycles", "3", "--out", tmp])` writes a valid `TopologyTimeline` JSON (parse it back, assert `n_cycles==3`).
- [ ] **Step 2 — confirm fail.**
- [ ] **Step 3 — implement** the `export-timeline` subcommand (load corpus via `io.py`, run `export_timeline` with the default reference adapters + ctx, write JSON). Then write `viewer/scripts/make_timeline.py` (header documents `cd .../protocol && uv run python ../viewer/scripts/make_timeline.py`): build a seed corpus that visibly grows + licenses over ≥8 cycles (mostly PENDING-with-plans + a proposer/injected so new nodes appear and statuses flip toward LICENSED; include a representation-revision that appears mid-timeline). Write `viewer/public/sample-timeline.json`; commit it.
- [ ] **Step 4 — green** (CLI tests + the local build/install smoke `scripts/build_and_test_install.sh` still passes) + ruff.
- [ ] **Step 5 — commit** `feat(cli): export-timeline command + sample timeline`.

**After 1–3 reviewed:** finish Branch A (merge local no-ff, no push).

---

## Branch B — `feat/live-timeline-viewer`

> After A merged: `cd /Users/zbb2/Desktop/polymer-claims && git checkout main && git checkout -b feat/live-timeline-viewer`

### Task 4: timeline store + types + loader

**Files:** `viewer/src/lib/timeline.ts`, `viewer/src/store.ts`.

- [ ] **Step 1:** `timeline.ts` — TS interfaces for `FrameStats`/`TimelineFrame`/`TopologyTimeline` + a loader for `public/sample-timeline.json`.
- [ ] **Step 2:** extend the zustand store: `timeline`, `playing`, `frame` (number), `speed`, `play/pause/seek/setSpeed`. Keep the static single-export path working (load `sample-topology.json` when no timeline).
- [ ] **Step 3:** `npx tsc --noEmit` clean. Commit `feat(viewer): timeline store + types`.

### Task 5: transport bar + frame interpolation + live readout

**Files:** `viewer/src/components/chrome/TransportBar.tsx`; modify `Nodes.tsx`, `Edges.tsx`, `ReadoutOverlay.tsx`, `ClaimUniverse.tsx`, `app/page.tsx`; a small `useInterpolatedFrame` hook.

- [ ] **Step 1 — TransportBar:** bottom-center, hairline D2, play/pause (electric blue), scrub slider over frames, mono `frame NN / NN` (tabular-nums), speed (0.5/1/2×), `§` marker. Wire to store (`play/pause/seek/setSpeed`). A ticker (rAF or an R3F `useFrame` driver) advances `frame` by `speed * dt` while `playing`, clamping at the last frame.
- [ ] **Step 2 — interpolation:** `useInterpolatedFrame(timeline, frame)` returns `{ nodes, edges, stats }` blended between `floor(frame)`→`ceil(frame)` at `t = frame-floor`: lerp node positions; nodes only in B → `enter` (scale 0→1, opacity 0→1); only in A → `exit` (→0); status color crossfade when changed; edges fade in/out, styling from the nearer frame. Feed `Nodes`/`Edges` this interpolated set (they currently take the static export — refactor to accept `{nodes, edges}`).
- [ ] **Step 3 — readout:** `ReadoutOverlay` shows the current frame's `FrameStats` (cycle index, n_nodes, per-status counts, edges eff/prov, frontier, `+N added`, `+N newly licensed`) + `layout_id`. Tabular-nums.
- [ ] **Step 4:** `npx tsc --noEmit` + `npm run build` clean; verify in-browser (press play → universe grows + licenses smoothly, no teleporting; scrub works; readout updates per frame). Commit `feat(viewer): transport bar + frame interpolation + live readout`.

**After 4–5 reviewed:** finish Branch B (merge local no-ff, no push).

## Self-Review
- Spec coverage: warm-start (T1), export_timeline+models (T2), CLI+sample (T3), store (T4), playback+interp+readout (T5). ✓
- No placeholders: signatures, the seed-init line, FrameStats fields, interpolation rule all concrete. ✓
- Determinism: seed positions passed in; export_timeline deterministic; animation time is client-side only. ✓
- Type consistency: `TopologyTimeline`/`TimelineFrame`/`FrameStats`, `export_timeline`, `seed_positions` used identically across tasks + viewer types mirror them. ✓
