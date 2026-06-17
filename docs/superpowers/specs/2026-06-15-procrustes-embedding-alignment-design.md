# Procrustes embedding alignment — the signed-Laplacian eigenmap as the live layout

> **Design spec, 2026-06-15.** Retires the "live-streaming stability" deferral from the relational-graph
> embedding (§8 of `docs/superpowers/archive/specs/2026-06-12-relational-graph-embedding-design.md`). Makes the
> signed-Laplacian spectral embedding the **live `NodeRunner` layout** (it was a static snapshot only),
> and **orthogonal-Procrustes-aligns** each incremental frame to the previous so the 3D universe evolves
> smoothly instead of thrashing. Umbrella-only (protocol untouched).
>
> **Status: shipped to `main`.** This is the design record; live build state + test counts in `docs/superpowers/CONTINUE.md`.

## Problem

`spectral_layout(corpus) -> dict[id → (x,y,z)]` (`src/polymer_claims/embedding.py`, the signed-Laplacian
eigenmap) gives claims **meaningful** relational positions, but it is only used for a **static** offline
sample. The live `NodeRunner` still lays out with force-directed Fruchterman-Reingold (warm-started by
`seed_positions`). Two gaps:

1. **The meaningful layout isn't live.** The viewer's live mode renders the FR layout, not the eigenmap.
2. **Naively recomputing the eigenmap each frame thrashes.** Eigenvectors are defined only up to sign
   (and up to rotation within a degenerate eigenspace); per-frame sign-canonicalization is computed from
   the current frame's largest-magnitude entry, so as the corpus changes the whole embedding can flip /
   rotate frame-to-frame — the universe spins instead of growing.

## Decision

- **Spectral becomes the live-node default layout** (decided). `NodeRunner(layout="spectral")` is the new
  default; `layout="force"` selects the prior force-directed behavior. (The deferred-analysis rec: the
  eigenmap is the meaningful one, so it should lead.)
- **Orthogonal Procrustes aligns each frame to the previous displayed frame.** On the common node set,
  find the orthogonal `R` (rotation **and reflection** — sign-flips are reflections we want to undo) that
  best maps the new raw positions onto the previous displayed positions, and apply it to all new nodes.
  This removes the per-frame basis ambiguity → consecutive frames differ only by the genuine corpus
  change, so the viewer's existing inter-frame interpolation reads as smooth growth.
- **Umbrella-only.** The protocol's `export_topology(positions=)` seam already injects external positions
  (`layout_id="external:spectral-v1"`); the protocol stays numpy-free.

## Approach (chosen: A)

- **A (chosen) — spectral as the NodeRunner default + orthogonal-Procrustes per frame.** A `procrustes_align`
  in `embedding.py`; the spectral branch in `node.py` (numpy lazy-imported); `serve --layout`.
- **B — opt-in mode (default force-directed).** Rejected by decision (spectral should lead).
- **C — recompute spectral each frame without Procrustes.** Rejected: that *is* the thrashing this slice
  fixes.

## Components

### `src/polymer_claims/embedding.py` (extend) — `procrustes_align`

```
procrustes_align(prev: dict[str, tuple], new: dict[str, tuple]) -> dict[str, tuple]
```
- `common = sorted(prev.keys() & new.keys())`. If `len(common) < 2` or `prev` is empty → return `new`
  unchanged (nothing to align to; underdetermined).
- Build `P` (prev common, n×3) and `Q` (new common, n×3) as numpy arrays. Center: `Pc = P − P.mean(0)`,
  `Qc = Q − Q.mean(0)`.
- `M = Qc.T @ Pc`; `U, _, Vt = np.linalg.svd(M)`; `R = U @ Vt` (orthogonal, det ±1 — reflection allowed,
  **no det-correction**).
- Apply to **all** new positions: `aligned[id] = (np.array(new[id]) − Q.mean(0)) @ R + P.mean(0)`, rounded
  to 6 dp (byte-stable, matching `spectral_layout`).
- Deterministic (numpy SVD is deterministic for a fixed matrix; the rounding pins cross-BLAS noise).
- numpy; lives beside `spectral_layout`, NOT re-exported from `__init__` (base import stays numpy-free).

### `src/polymer_claims/node.py` (extend) — spectral layout mode

- `NodeRunner.__init__(..., layout: Literal["spectral", "force"] = "spectral")`. New state
  `self._prev_spectral: dict[str, tuple] = {}` (the previous **displayed** spectral positions, for the
  Procrustes chain).
- A private `self._spectral_positions(corpus) -> dict` helper: **lazy-imports** `spectral_layout` +
  `procrustes_align` (keeps `node.py` base import numpy-free); computes raw spectral positions,
  `procrustes_align`s them to `self._prev_spectral`, stores + returns the aligned dict. Frame 0 (empty
  `_prev_spectral`) → returns the raw spectral positions (the reference).
- Both the `__init__` frame-0 build and `tick()` choose the layout:
  - `layout == "spectral"`: `topo = export_topology(corpus, layout=Layout.FORCE_DIRECTED,
    positions=self._spectral_positions(corpus))` (the `positions=` override sets `layout_id`
    `external:spectral-v1`; `layout`/`seed_positions` are ignored when `positions` is supplied).
  - `layout == "force"`: today's exact path (`export_topology(corpus, layout=Layout.FORCE_DIRECTED,
    seed_positions=self.prev_positions)`), byte-identical.
- **Graceful fallback:** if the lazy embedder import fails (`ImportError` — numpy/`[embed]` absent), spectral
  mode falls back to the force path for that node and records the actual layout (the frame's `layout_id`
  is self-describing). `serve` therefore never breaks without `[embed]`; with `[embed]` (the dev default)
  spectral leads. (One-line behavior; logged once.)

### `src/polymer_claims/cli.py` (extend) — `serve --layout`

- `serve` gains `--layout {spectral,force}` (default `spectral`) → `NodeRunner(layout=...)`. The viewer is
  unchanged — positions are positions; it renders whatever the SSE frames carry.

### `viewer/scripts/make_spectral_timeline.py` (create) — demo artifact

- Mirror `make_spectral_sample.py` but multi-frame: drive an evolving seed corpus through a few cycles,
  spectral + Procrustes each frame, write `viewer/public/sample-spectral-timeline.json` (a
  `TopologyTimeline`) so the smooth evolution is watchable in sample mode.

## Out of scope / accepted asymmetry

- The offline `export_timeline` (`protocol/.../timeline.py`, numpy-free) **stays force-directed** — it
  cannot compute the spectral embedding (protocol purity). The live `NodeRunner` (umbrella) is where
  spectral lives. This asymmetry was accepted in the wiring decision.
- UMAP / content features (still deferred from the embedding spec §8).
- No new viewer code (the viewer already interpolates between frames).

## Invariants preserved

- **protocol untouched + numpy-free** (`export_topology`'s `positions=` seam already exists); **Corpus = 4**.
- **`node.py` base import stays numpy-free** — the embedder is lazy-imported only when a spectral frame is
  built (mirrors the CES-4 lazy methyl import). `import polymer_claims` pulls no numpy.
- **`layout="force"` is byte-identical** to today's NodeRunner; the force path is untouched.
- Spectral positions remain **deterministic** (sign-canonicalized eigenmap + Procrustes SVD + 6dp round).

## Acceptance criteria

1. `procrustes_align` recovers orientation: given `new` = a known rotation+reflection of `prev` (same
   ids), the aligned output matches `prev` (within 1e-6) on the common nodes.
2. **Anti-thrash proof:** a `NodeRunner(layout="spectral")` driven N ticks over an evolving corpus has
   **small/bounded** max per-node displacement on common nodes between consecutive frames, and that bound
   is **strictly smaller** than the same run with Procrustes disabled (raw spectral) — demonstrating the
   alignment kills the eigenbasis thrashing.
3. A spectral-mode frame carries `layout_id == "external:spectral-v1"` and meaningful (non-origin)
   positions; the corpus still licenses/evolves identically (layout doesn't touch the run loop).
4. `NodeRunner(layout="force")` is byte-identical to the current default behavior (existing force tests,
   updated to pass `layout="force"`, stay green).
5. `serve --layout spectral` constructs a spectral NodeRunner; `--layout force` the force one.
6. `node.py` base import is numpy-free; protocol untouched; Corpus = 4; `scripts/check-all.sh` ALL GREEN.

## Anchored file map (for the plan)

- `src/polymer_claims/embedding.py` — `procrustes_align` (beside `spectral_layout`).
- `src/polymer_claims/node.py` — `layout` param, `_prev_spectral` state, `_spectral_positions` helper,
  spectral branch in `__init__` frame-0 + `tick()`, graceful fallback.
- `src/polymer_claims/cli.py` — `serve --layout`.
- `viewer/scripts/make_spectral_timeline.py` — demo artifact + `viewer/public/sample-spectral-timeline.json`.
- Existing tests to update with explicit `layout="force"`: `tests/test_node*.py`, `tests/test_serve*.py`
  (whichever assert force-directed `layout_id`/positions) — audit in the plan.
- Reference precedents: `viewer/scripts/make_spectral_sample.py` (the spectral→positions= pattern),
  `protocol/.../timeline.py:export_timeline` (the warm-start frame chain), `embedding.py`
  (`spectral_layout`, `_canonicalize_columns`, the 6dp rounding idiom),
  `protocol/.../topology.py:export_topology` (the `positions=` seam, `layout_id`).
