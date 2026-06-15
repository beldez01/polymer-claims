# Procrustes embedding alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the signed-Laplacian spectral eigenmap the live `NodeRunner` layout, orthogonal-Procrustes-aligned frame-to-frame so the 3D claims-universe grows smoothly instead of thrashing.

**Architecture:** Add `procrustes_align` beside `spectral_layout` in the impure (numpy) `embedding.py`. Give `NodeRunner` a `layout` param (`"spectral"` default, `"force"` = today's exact path) that lazy-imports the embedder, aligns each raw eigenmap frame to the previous displayed one, and injects the result through the protocol's existing `export_topology(positions=)` seam (`layout_id="external:spectral-v1"`). Protocol stays numpy-free and untouched; `node.py`'s base import stays numpy-free; spectral gracefully falls back to force when `[embed]`/numpy is absent.

**Tech Stack:** Python, numpy (umbrella-only, lazy-imported), pydantic models (`TopologyExport`/`TopologyTimeline`), pytest.

---

## File Structure

- `src/polymer_claims/embedding.py` (modify) — add `procrustes_align` next to `spectral_layout`. Stays numpy, NOT re-exported from `__init__`.
- `src/polymer_claims/node.py` (modify) — `layout` param threaded through `__init__` + `from_seed`; `_prev_spectral` state; `_spectral_positions` + `_layout_topology` helpers (lazy embedder import, graceful fallback); frame-0 and `tick()` route through `_layout_topology`.
- `src/polymer_claims/cli.py` (modify) — `serve --layout {spectral,force}` (default `spectral`), threaded into the three `NodeRunner.from_seed(...)` call sites in `_cmd_serve`.
- `src/polymer_claims/_synthetic_corpus.py` (modify) — add `growing_cluster0_corpora()`: the shared "reveal the dense `c0_*` cluster one claim at a time" fixture (a growing-≥4-component corpus sequence) used by both AC#2's test and the demo timeline.
- `viewer/scripts/make_spectral_timeline.py` (create) — multi-frame demo artifact → `viewer/public/sample-spectral-timeline.json`.
- `tests/test_embedding.py` (modify) — `procrustes_align` unit tests (AC#1).
- `tests/test_node.py` (modify) — existing force-behavior tests pinned to `layout="force"` (AC#4).
- `tests/test_node_spectral.py` (create) — spectral layout_id/positions (AC#3), anti-thrash proof (AC#2), force byte-identity assertion (AC#4), graceful fallback.
- `tests/test_serve_cli.py` (modify) — `serve --layout` threads into the runner (AC#5).

> **Background facts the implementer needs (verified against the code, do not re-derive):**
> - The protocol seam already exists: `export_topology(corpus, ..., positions=<dict>)` sets every node's coordinate from the dict (missing id → origin), sets `layout_id="external:spectral-v1"`, and **ignores** `layout`/`seed_positions`. See `protocol/src/polymer_protocol/topology.py:310`+.
> - In the force path, `seed_positions={}` is byte-identical to `seed_positions=None`: `_force_directed_layout` does `seed_suffix = "warm" if seed_positions else "sha256"` and `(seed_positions or {})`, so an empty dict and `None` both yield `seed=sha256` and identical positions. This is why routing frame-0 through a helper that passes `seed_positions=self.prev_positions` (which is `{}` at frame 0) stays byte-identical to today's `export_topology(corpus, layout=Layout.FORCE_DIRECTED)`.
> - `spectral_layout(corpus)` already rounds to 6dp and is deterministic/sign-canonicalized (`embedding.py:145`). `procrustes_align` must match that 6dp rounding.
> - `NodeRunner.from_seed` (`node.py:112`) is the constructor used everywhere (tests + `cli.py`), so `layout` MUST be threaded through it, not only `__init__`.
> - The numpy-free base-import guard already exists: `tests/test_node_evalue_gate.py::test_node_import_stays_numpy_free` spawns a subprocess asserting `'numpy' not in sys.modules` after `import polymer_claims.node`. Keeping the embedder import lazy (inside `_spectral_positions`) preserves it — AC#6.

---

## Design note — AC#2 corpus choice (READ THIS; it changes the test/demo corpus vs the spec's literal wording)

The spec's AC#2 says "a `NodeRunner(layout="spectral")` driven N ticks over an **evolving corpus**." Empirically (measured against the code), the **default `serve` seed** (`default_seed_corpus`) is the **wrong corpus** to demonstrate the anti-thrash mechanism, and the literal test would fail or pass vacuously:

- Its largest connected component **caps at size 3** — it never crosses the `n < 4` eigenmap threshold (`embedding.py:121`), so every node uses the `_hash_ball` fallback. There is **no eigenmap and therefore no eigenbasis sign/rotation thrash** to undo.
- The frame-to-frame churn that *does* exist on the default seed is **lattice reindexing** (`side = ceil(n_comps ** (1/3))` changes as components are added → every component's grid slot jumps) plus **global rescale**. These are non-rigid, per-component motions. Measured: orthogonal Procrustes makes it **worse** (3.09 vs raw 2.56); even similarity-with-scale doesn't beat raw (2.64). No single global transform can fix per-component lattice jumps.

The mechanism Procrustes is for — eigenbasis sign-flips — only appears when a **≥4-node connected component grows**. So AC#2's test and the demo timeline use the planted corpus's dense `c0_*` cluster, **revealed one claim at a time** (component grows `2→3→4→7→8`). Measured on that sequence: raw thrash **2.70**, Procrustes-aligned **1.27** (< half) — deterministic. This is the honest demonstration of the mechanism, and it is consistent with the original `2026-06-12` spec's harness, which uses this same `planted_corpus` as its meaningful-embedding fixture.

**Accepted consequence (document, don't hide):** spectral remains the live `NodeRunner` default per the `06-15` spec's decision, but on the *small default `serve` seed* it will not look smoother than force (the corpus never reaches the eigenmap). `--layout force` is the escape hatch and the viewer interpolates frames regardless. AC#3's NodeRunner-integration test therefore runs on the default seed and asserts only the integration contract (`layout_id`, non-origin positions, determinism, evolution) — NOT a thrash reduction. The two concerns are split: **AC#2 = mechanism** (growing-component corpus, no `NodeRunner`), **AC#3 = integration** (`NodeRunner` over the default seed).

---

## Task 1: `procrustes_align` in embedding.py

**Files:**
- Modify: `src/polymer_claims/embedding.py` (add function after `spectral_layout`, end of file ~line 166)
- Test: `tests/test_embedding.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_embedding.py`:

```python
def test_procrustes_align_recovers_rotation_and_reflection():
    import numpy as np
    from polymer_claims.embedding import procrustes_align

    # 4 non-coplanar points (rank-3 → recovery is exact)
    prev = {
        "a": (0.1, 0.2, 0.3),
        "b": (-0.4, 0.5, -0.1),
        "c": (0.7, -0.2, 0.6),
        "d": (-0.3, -0.5, 0.2),
    }
    # An orthogonal matrix with det = -1 (a rotation composed with a reflection)
    G = np.array([
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, -1.0],
    ])
    assert round(float(np.linalg.det(G)), 6) == -1.0
    new = {k: tuple(np.asarray(v) @ G) for k, v in prev.items()}

    aligned = procrustes_align(prev, new)

    assert set(aligned) == set(prev)
    for k in prev:
        for got, want in zip(aligned[k], prev[k]):
            assert abs(got - want) < 1e-6


def test_procrustes_align_underdetermined_returns_new_unchanged():
    from polymer_claims.embedding import procrustes_align

    # fewer than 2 common ids → nothing to align to → new returned unchanged
    assert procrustes_align({}, {"x": (1.0, 2.0, 3.0)}) == {"x": (1.0, 2.0, 3.0)}
    assert procrustes_align({"a": (0.0, 0.0, 0.0)}, {"b": (1.0, 1.0, 1.0)}) == {"b": (1.0, 1.0, 1.0)}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_embedding.py::test_procrustes_align_recovers_rotation_and_reflection tests/test_embedding.py::test_procrustes_align_underdetermined_returns_new_unchanged -v`
Expected: FAIL with `ImportError: cannot import name 'procrustes_align'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/polymer_claims/embedding.py`:

```python
def procrustes_align(
    prev: dict[str, tuple[float, float, float]],
    new: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]]:
    """Orthogonal-Procrustes-align ``new`` spectral positions onto ``prev`` (the previously
    displayed frame) on their common nodes, then apply that single orthogonal transform to ALL
    of ``new``.

    Eigenvectors are defined only up to sign (and rotation within a degenerate eigenspace), so a
    naive per-frame recompute can flip/rotate the whole embedding frame-to-frame. We find the
    orthogonal R (rotation AND reflection — sign-flips are reflections we WANT to undo, so there is
    deliberately NO det-correction) best mapping the new common positions onto the previous ones,
    so consecutive frames differ only by the genuine corpus change.

    Underdetermined (``prev`` empty, or fewer than 2 common ids) → return ``new`` unchanged: this is
    the frame-0 reference. Output rounded to 6dp to match ``spectral_layout`` (byte-stable; pins
    cross-BLAS float noise). Deterministic for a fixed input (numpy SVD is deterministic)."""
    common = sorted(prev.keys() & new.keys())
    if not prev or len(common) < 2:
        return new

    P = np.array([prev[c] for c in common], dtype=float)  # n x 3 (target, previous frame)
    Q = np.array([new[c] for c in common], dtype=float)    # n x 3 (source, new raw frame)
    p_mean = P.mean(axis=0)
    q_mean = Q.mean(axis=0)
    Pc = P - p_mean
    Qc = Q - q_mean

    M = Qc.T @ Pc                  # 3 x 3
    U, _, Vt = np.linalg.svd(M)
    R = U @ Vt                     # orthogonal, det ±1 — reflection allowed, NO det-correction

    aligned: dict[str, tuple[float, float, float]] = {}
    for nid, xyz in new.items():
        v = (np.array(xyz, dtype=float) - q_mean) @ R + p_mean
        aligned[nid] = tuple(round(float(c), 6) for c in v)
    return aligned
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_embedding.py -v`
Expected: PASS (the two new tests + all existing embedding tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/embedding.py tests/test_embedding.py
git commit -m "feat(embedding): add orthogonal-Procrustes alignment for spectral frames"
```

---

## Task 2: Spectral layout mode in NodeRunner

**Files:**
- Modify: `src/polymer_claims/node.py` (imports ~line 16; `__init__` signature ~line 56-69; state init ~line 86-88; frame-0 build line 91; `from_seed` ~line 112-138; `tick()` topology build lines 199-203; add `_spectral_positions` + `_layout_topology` helpers)
- Modify: `src/polymer_claims/_synthetic_corpus.py` (add `growing_cluster0_corpora()` fixture for AC#2)
- Modify: `tests/test_node.py` (pin existing force tests to `layout="force"`)
- Test: `tests/test_node_spectral.py` (create)

### Step group A — implementation

- [ ] **Step 1: Add imports for `Literal` and logging**

In `src/polymer_claims/node.py`, the file currently starts its imports at line 16 with `from __future__ import annotations`. Add a stdlib block right after it:

Find:
```python
from __future__ import annotations

from polymer_grammar import IdentityAdapter, MaterializationContext, ReferenceAdapter
```
Replace with:
```python
from __future__ import annotations

import logging
from typing import Literal

from polymer_grammar import IdentityAdapter, MaterializationContext, ReferenceAdapter
```

Then, immediately after the existing module-level constants (the block ending with `_CTX = MaterializationContext(id="M1", api_version="v1", data_version="d1")`, ~line 41), add:

```python
logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Add the `layout` parameter to `__init__`**

In `NodeRunner.__init__` (signature at line 56), add `layout` as a keyword-only parameter. Find the signature line:
```python
        evalue_gate: bool = False,
        **run_cycle_kwargs,
    ) -> None:
```
Replace with:
```python
        evalue_gate: bool = False,
        layout: Literal["spectral", "force"] = "spectral",
        **run_cycle_kwargs,
    ) -> None:
```

- [ ] **Step 3: Initialise spectral state (before the frame-0 build)**

In `__init__`, find:
```python
        self.frame_index = 0
        self.prev_positions: dict[str, tuple] = {}
        self.running = True

        # Frame 0 — the seed snapshot (no warm-start positions yet).
        topo = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
```
Replace with:
```python
        self.frame_index = 0
        self.prev_positions: dict[str, tuple] = {}
        self.layout = layout
        # Previously DISPLAYED spectral positions — the Procrustes alignment target chain.
        self._prev_spectral: dict[str, tuple] = {}
        self._spectral_fallback_warned = False
        self.running = True

        # Frame 0 — the seed snapshot (no warm-start positions yet).
        topo = self._layout_topology(corpus)
```

- [ ] **Step 4: Thread `layout` through `from_seed`**

In `from_seed` (classmethod at line 112), add the parameter and pass it through. Find:
```python
        evalue_gate: bool = False,
        **run_cycle_kwargs,
    ) -> "NodeRunner":
        return cls(
            corpus,
            adapters=adapters,
            ctx=ctx,
            config=config,
            scheduler_budget=scheduler_budget,
            max_frames=max_frames,
            content_address=content_address,
            profiles=profiles,
            evalue_gate=evalue_gate,
            **run_cycle_kwargs,
        )
```
Replace with:
```python
        evalue_gate: bool = False,
        layout: Literal["spectral", "force"] = "spectral",
        **run_cycle_kwargs,
    ) -> "NodeRunner":
        return cls(
            corpus,
            adapters=adapters,
            ctx=ctx,
            config=config,
            scheduler_budget=scheduler_budget,
            max_frames=max_frames,
            content_address=content_address,
            profiles=profiles,
            evalue_gate=evalue_gate,
            layout=layout,
            **run_cycle_kwargs,
        )
```

- [ ] **Step 5: Route `tick()`'s topology build through the helper**

In `tick()`, find:
```python
        self.frame_index += 1
        topo = export_topology(
            self.corpus,
            layout=Layout.FORCE_DIRECTED,
            seed_positions=self.prev_positions,
        )
```
Replace with:
```python
        self.frame_index += 1
        topo = self._layout_topology(self.corpus)
```

- [ ] **Step 6: Add the `_spectral_positions` and `_layout_topology` helpers**

Add these two methods to `NodeRunner` (place them immediately before `def snapshot` at line 223):

```python
    def _spectral_positions(self, corpus: Corpus) -> dict[str, tuple]:
        """Raw signed-Laplacian eigenmap positions, orthogonal-Procrustes-aligned to the previous
        displayed spectral frame (kills the per-frame eigenbasis sign/rotation thrash). The numpy
        embedder is LAZY-imported here so `node.py`'s base import stays numpy-free (mirrors the
        evalue_gate lazy methyl import). Frame 0 (empty `_prev_spectral`) → the raw reference.

        Raises ImportError if numpy / the `[embed]` extra is absent (caller handles fallback)."""
        from .embedding import procrustes_align, spectral_layout  # lazy: base import stays numpy-free

        raw = spectral_layout(corpus)
        aligned = procrustes_align(self._prev_spectral, raw)
        self._prev_spectral = aligned
        return aligned

    def _layout_topology(self, corpus: Corpus):
        """Export a topology frame for the chosen layout.

        - "spectral": inject Procrustes-aligned eigenmap positions through the protocol's
          `positions=` seam (`layout_id="external:spectral-v1"`). If the numpy embedder is
          unavailable (ImportError — numpy/`[embed]` absent) fall back to the force path for this
          frame (logged once); the frame's `layout_id` is self-describing.
        - "force": today's EXACT warm-started Fruchterman-Reingold path. `self.prev_positions` is
          `{}` at frame 0, which `export_topology` treats identically to `seed_positions=None`, so
          this is byte-identical to the historical behaviour."""
        if self.layout == "spectral":
            try:
                positions = self._spectral_positions(corpus)
            except ImportError:
                if not self._spectral_fallback_warned:
                    logger.warning(
                        "spectral layout unavailable (numpy/[embed] missing); "
                        "falling back to force-directed"
                    )
                    self._spectral_fallback_warned = True
            else:
                return export_topology(
                    corpus, layout=Layout.FORCE_DIRECTED, positions=positions
                )
        return export_topology(
            corpus, layout=Layout.FORCE_DIRECTED, seed_positions=self.prev_positions
        )
```

### Step group B — pin existing force tests (AC#4)

- [ ] **Step 7: Update `tests/test_node.py` to request the force layout**

The existing tests assert force-directed warm-start behaviour, so they must keep exercising the force path. Update the four `NodeRunner.from_seed(...)` calls to pass `layout="force"`.

Find (test 1):
```python
def test_node_runner_ticks_and_accumulates():
    r = NodeRunner.from_seed(licensing_corpus())
```
Replace with:
```python
def test_node_runner_ticks_and_accumulates():
    r = NodeRunner.from_seed(licensing_corpus(), layout="force")
```

Find (test 2):
```python
def test_node_runner_snapshot_is_valid_before_ticks():
    r = NodeRunner.from_seed(licensing_corpus())
```
Replace with:
```python
def test_node_runner_snapshot_is_valid_before_ticks():
    r = NodeRunner.from_seed(licensing_corpus(), layout="force")
```

Find (test 3):
```python
    r = NodeRunner.from_seed(licensing_corpus(), max_frames=5)
```
Replace with:
```python
    r = NodeRunner.from_seed(licensing_corpus(), max_frames=5, layout="force")
```

Find (test 4):
```python
    r = NodeRunner.from_seed(licensing_corpus(), max_frames=None)
```
Replace with:
```python
    r = NodeRunner.from_seed(licensing_corpus(), max_frames=None, layout="force")
```

- [ ] **Step 8: Run the force tests to verify they still pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_node.py -v`
Expected: PASS (force path unchanged, byte-identical behaviour preserved).

### Step group C — shared growing-corpus fixture (AC#2)

- [ ] **Step 9: Add `growing_cluster0_corpora()` to `_synthetic_corpus.py`**

This is the shared fixture for AC#2's mechanism test AND the demo timeline (Task 4): the dense `c0_*` cluster of the planted corpus, revealed one claim at a time, so the connected component grows across the `n>=4` eigenmap threshold (measured: `2→3→4→7→8`) and the eigenvectors recompute / sign-canonicalisation flips frame-to-frame — the eigenbasis thrash Procrustes exists to kill. `Corpus` is already imported in this module (it's what `planted_corpus` returns).

Append to `src/polymer_claims/_synthetic_corpus.py`:

```python
# Reveal order for the dense cluster-0 subgraph (see planted_corpus): each prefix is a valid
# Corpus whose largest connected component grows 2 -> 3 -> 4 -> 7 -> 8, crossing the n>=4 eigenmap
# threshold so the signed-Laplacian basis genuinely recomputes/flips between frames.
_CLUSTER0_REVEAL = ("c0_0", "c0_1", "c0_2", "c0_3", "c0_4", "c0_5", "c0_6", "c0_7")


def growing_cluster0_corpora() -> list[Corpus]:
    """A deterministic sequence of growing sub-corpora built from planted_corpus's c0_* cluster.

    Each step reveals one more claim (starting from the first 4) and keeps only the defeat edges /
    equivalences whose endpoints are present, so every sub-corpus validates. Used to demonstrate
    the Procrustes anti-thrash mechanism on a genuinely growing >=4-node component (the default
    serve seed caps at a 3-node component and never reaches the eigenmap)."""
    pc = planted_corpus()
    by_id = {c.id: c for c in pc.claims}
    out: list[Corpus] = []
    for k in range(4, len(_CLUSTER0_REVEAL) + 1):
        present = set(_CLUSTER0_REVEAL[:k])
        sub_defeat = tuple(
            e for e in pc.defeat_edges if e.source in present and e.target in present
        )
        sub_equiv = tuple(
            e for e in pc.equivalences if e.left in present and e.right in present
        )
        out.append(
            Corpus(
                claims=tuple(by_id[i] for i in _CLUSTER0_REVEAL[:k]),
                fdr_ledger=pc.fdr_ledger,
                defeat_edges=sub_defeat,
                equivalences=sub_equiv,
            )
        )
    return out
```

- [ ] **Step 10: Smoke-check the fixture from a shell (not a committed test)**

Run:
```bash
cd /Users/zbb2/Desktop/polymer-claims && uv run --project . python -c "
from polymer_claims._synthetic_corpus import growing_cluster0_corpora
from polymer_claims.embedding import build_graph, _components
seq = growing_cluster0_corpora()
sizes = [max((len(c) for c in _components(*build_graph(s)[:2])), default=0) for s in seq]
print('largest-component sizes:', sizes)
assert sizes == [2, 3, 4, 7, 8], sizes
print('ok')
"
```
Expected: `largest-component sizes: [2, 3, 4, 7, 8]` then `ok`.

### Step group D — spectral tests (AC#2 mechanism, AC#3 integration, AC#4 force, fallback)

- [ ] **Step 11: Write the failing spectral tests**

Create `tests/test_node_spectral.py`:

```python
"""Spectral live layout: Procrustes anti-thrash on a growing >=4-node component (the mechanism),
plus NodeRunner integration over the default seed (layout_id / positions / determinism / evolution),
force byte-identity, and graceful fallback when the numpy embedder is absent."""
from __future__ import annotations

import sys

from polymer_claims.node import NodeRunner
from polymer_claims.seed import default_seed_corpus
from polymer_claims._synthetic_corpus import growing_cluster0_corpora


def _max_consecutive_disp(seq):
    """Max per-node displacement on common nodes across consecutive id->position dicts."""
    m = 0.0
    for a, b in zip(seq, seq[1:]):
        for nid in a.keys() & b.keys():
            d = sum((x - y) ** 2 for x, y in zip(a[nid], b[nid])) ** 0.5
            m = max(m, d)
    return m


def test_procrustes_kills_eigenbasis_thrash_on_growing_component():
    # AC#2 (mechanism): over a corpus whose connected component grows across the n>=4 eigenmap
    # threshold, the Procrustes-aligned chain has strictly smaller (with margin) and bounded
    # consecutive displacement than the raw per-frame eigenmap — i.e. the alignment kills the
    # eigenbasis sign/rotation thrash. Deterministic (sign-canonicalised eigenmap + SVD + 6dp).
    # NOTE: this exercises the mechanism directly, NOT via NodeRunner.tick(), because the default
    # serve seed never grows a >=4 component (see the plan's design note); AC#3 below covers the
    # NodeRunner integration path.
    from polymer_claims.embedding import spectral_layout, procrustes_align

    corpora = growing_cluster0_corpora()
    raw = [spectral_layout(c) for c in corpora]
    aligned = [raw[0]]
    prev = raw[0]
    for r in raw[1:]:
        a = procrustes_align(prev, r)
        aligned.append(a)
        prev = a

    raw_max = _max_consecutive_disp(raw)
    aligned_max = _max_consecutive_disp(aligned)

    # Non-vacuous: the raw eigenmap must actually thrash (the basis flips as the component grows).
    assert raw_max > 0.5, f"corpus did not exercise eigenbasis thrash (raw_max={raw_max})"
    # Strictly smaller, with comfortable margin (measured ~1.27 vs ~2.70).
    assert aligned_max < 0.75 * raw_max, f"alignment margin too small: {aligned_max} vs {raw_max}"


def test_aligned_chain_is_deterministic():
    # The Procrustes chain is deterministic for a fixed corpus sequence (byte-stable).
    from polymer_claims.embedding import spectral_layout, procrustes_align

    def chain():
        corpora = growing_cluster0_corpora()
        raw = [spectral_layout(c) for c in corpora]
        out = [raw[0]]
        prev = raw[0]
        for r in raw[1:]:
            a = procrustes_align(prev, r)
            out.append(a)
            prev = a
        return out

    assert chain() == chain()


def test_spectral_nodeRunner_frame_is_external_and_nonorigin():
    # AC#3 (integration): a spectral-mode NodeRunner frame is tagged external:spectral-v1 with
    # meaningful (non-origin) positions, and the corpus still evolves (licensing is layout-blind).
    corpus, kwargs = default_seed_corpus()
    runner = NodeRunner.from_seed(corpus, layout="spectral", **kwargs)
    for _ in range(8):
        runner.tick()
    tl = runner.snapshot()

    last = tl.frames[-1]
    assert last.topology.layout_id == "external:spectral-v1"
    assert any(any(abs(c) > 1e-9 for c in n.position) for n in last.topology.nodes)
    assert tl.frames[-1].stats.n_licensed >= tl.frames[0].stats.n_licensed


def test_spectral_nodeRunner_is_deterministic():
    # Two identical spectral runs produce byte-identical timelines (determinism through the runner).
    def run():
        corpus, kwargs = default_seed_corpus()
        r = NodeRunner.from_seed(corpus, layout="spectral", **kwargs)
        for _ in range(6):
            r.tick()
        return r.snapshot().model_dump_json()

    assert run() == run()


def test_force_layout_is_fruchterman_reingold():
    # AC#4: layout="force" produces the historical FR layout_id (byte-identical force path).
    corpus, kwargs = default_seed_corpus()
    runner = NodeRunner.from_seed(corpus, layout="force", **kwargs)
    runner.tick()
    assert runner.frames[-1].topology.layout_id.startswith("fruchterman-reingold")


def test_spectral_falls_back_to_force_without_embedder(monkeypatch):
    # Graceful fallback: if the lazy embedder import fails, spectral mode uses the force path and
    # records the actual (FR) layout_id. Setting the module to None makes `import` raise ImportError.
    monkeypatch.setitem(sys.modules, "polymer_claims.embedding", None)
    corpus, kwargs = default_seed_corpus()
    runner = NodeRunner.from_seed(corpus, layout="spectral", **kwargs)
    assert runner.frames[0].topology.layout_id.startswith("fruchterman-reingold")
```

- [ ] **Step 12: Run test to verify it passes (after Steps 1-9)**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_node_spectral.py -v`
Expected: PASS (all six tests).

> If `test_procrustes_kills_eigenbasis_thrash_on_growing_component` fails the `raw_max > 0.5` guard, the planted-corpus reveal didn't grow a ≥4 component — re-run Step 10's smoke check; the sizes MUST be `[2, 3, 4, 7, 8]`. Do NOT weaken the guards; fix the fixture.

- [ ] **Step 13: Verify the base import stays numpy-free (AC#6 regression guard)**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_node_evalue_gate.py::test_node_import_stays_numpy_free -v`
Expected: PASS (the embedder is lazy-imported inside `_spectral_positions`, so `import polymer_claims.node` still pulls no numpy).

- [ ] **Step 14: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/node.py src/polymer_claims/_synthetic_corpus.py tests/test_node.py tests/test_node_spectral.py
git commit -m "feat(node): spectral layout default with Procrustes alignment + graceful fallback"
```

---

## Task 3: `serve --layout` CLI flag

**Files:**
- Modify: `src/polymer_claims/cli.py` (parser ~line 364; `_cmd_serve` `from_seed` call sites at lines 235, 264, 279)
- Test: `tests/test_serve_cli.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_serve_cli.py`:

```python
def test_serve_layout_threads_into_runner(monkeypatch):
    seen = {}

    def fake_import():
        def run(app, host=None, port=None):
            seen["bind"] = (host, port)
        def create_app(runner, *, interval, origins):
            seen["runner"] = runner
            return "APP"
        return types.SimpleNamespace(run=run), create_app

    monkeypatch.setattr(cli, "_import_server", fake_import)

    rc = main(["serve", "--layout", "force", "--port", "1234"])
    assert rc == 0
    assert seen["runner"].layout == "force"

    rc = main(["serve", "--layout", "spectral", "--port", "1235"])
    assert rc == 0
    assert seen["runner"].layout == "spectral"


def test_serve_layout_defaults_to_spectral(monkeypatch):
    seen = {}

    def fake_import():
        def run(app, host=None, port=None):
            seen["bind"] = (host, port)
        def create_app(runner, *, interval, origins):
            seen["runner"] = runner
            return "APP"
        return types.SimpleNamespace(run=run), create_app

    monkeypatch.setattr(cli, "_import_server", fake_import)
    rc = main(["serve", "--port", "1236"])
    assert rc == 0
    assert seen["runner"].layout == "spectral"
```

> `types` is already imported in `tests/test_serve_cli.py` (used by `test_serve_builds_runner_and_runs`). Confirm the import is present at the top; if not, add `import types`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_serve_cli.py::test_serve_layout_threads_into_runner -v`
Expected: FAIL — argparse errors on the unknown `--layout` argument (SystemExit), so `rc` is never 0.

- [ ] **Step 3: Add the `--layout` argument to the serve parser**

In `src/polymer_claims/cli.py`, find (the last serve argument before `set_defaults`, ~line 363):
```python
    p_serve.add_argument("--llm-every", type=int, default=4, help="LLM proposes every Nth tick (throttle)")
    p_serve.set_defaults(func=_cmd_serve)
```
Replace with:
```python
    p_serve.add_argument("--llm-every", type=int, default=4, help="LLM proposes every Nth tick (throttle)")
    p_serve.add_argument(
        "--layout",
        choices=("spectral", "force"),
        default="spectral",
        help="live layout: spectral (signed-Laplacian eigenmap, Procrustes-aligned; default) or force (Fruchterman-Reingold)",
    )
    p_serve.set_defaults(func=_cmd_serve)
```

- [ ] **Step 4: Thread `args.layout` into the three `from_seed` call sites**

In `_cmd_serve`, all three `NodeRunner.from_seed(...)` calls must pass `layout=args.layout`.

Find (real-data branch, ~line 235):
```python
        runner = NodeRunner.from_seed(
            corpus,
            adapters=(StatsPureAdapter(), StatsStdlibAdapter()),
            ctx=_CTX,
            scheduler_budget=args.budget,
            max_frames=args.max_frames,
            adapter_registry=independent_registry(),
            oracles=apparatus_oracle_registry(),
            proposers=(proposer,),
            **seed_kwargs,
        )
```
Replace with:
```python
        runner = NodeRunner.from_seed(
            corpus,
            adapters=(StatsPureAdapter(), StatsStdlibAdapter()),
            ctx=_CTX,
            scheduler_budget=args.budget,
            max_frames=args.max_frames,
            adapter_registry=independent_registry(),
            oracles=apparatus_oracle_registry(),
            proposers=(proposer,),
            layout=args.layout,
            **seed_kwargs,
        )
```

Find (seed-corpus branch, ~line 264):
```python
        runner = NodeRunner.from_seed(
            corpus,
            scheduler_budget=args.budget,
            max_frames=args.max_frames,
            **seed_kwargs,
        )
```
Replace with:
```python
        runner = NodeRunner.from_seed(
            corpus,
            scheduler_budget=args.budget,
            max_frames=args.max_frames,
            layout=args.layout,
            **seed_kwargs,
        )
```

Find (default-seed branch, ~line 279):
```python
        runner = NodeRunner.from_seed(
            corpus, scheduler_budget=args.budget, max_frames=args.max_frames, **kwargs
        )
```
Replace with:
```python
        runner = NodeRunner.from_seed(
            corpus, scheduler_budget=args.budget, max_frames=args.max_frames, layout=args.layout, **kwargs
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . pytest tests/test_serve_cli.py -v`
Expected: PASS (new layout tests + all existing serve tests).

- [ ] **Step 6: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add src/polymer_claims/cli.py tests/test_serve_cli.py
git commit -m "feat(cli): serve --layout {spectral,force} (default spectral)"
```

---

## Task 4: `make_spectral_timeline.py` demo artifact

**Files:**
- Create: `viewer/scripts/make_spectral_timeline.py`
- Create (generated): `viewer/public/sample-spectral-timeline.json`

- [ ] **Step 1: Create the demo script**

This builds a watchable multi-frame `TopologyTimeline` over the growing `c0_*` component (the corpus where Procrustes-aligned spectral genuinely shows SMOOTH growth — see the design note). It drives the spectral+Procrustes chain directly (not `NodeRunner`, which can't grow `c0_*` incrementally) and assembles `TimelineFrame`s the same way `NodeRunner` does (`export_topology(positions=)` + `frame_stats`). Companion to `make_spectral_sample.py` (single static frame).

Create `viewer/scripts/make_spectral_timeline.py`:

```python
"""Generate a MULTI-FRAME spectral TopologyTimeline for the viewer.

Reveals the planted corpus's dense c0_* cluster one claim at a time, laying out each frame with the
signed-Laplacian eigenmap orthogonal-Procrustes-aligned to the previous frame, and writes the
accumulated TopologyTimeline to viewer/public/sample-spectral-timeline.json — so the SMOOTH growth
(no eigenbasis thrash) is watchable in the viewer's sample mode. Companion to make_spectral_sample.py.

RUN (from the UMBRELLA env so polymer_claims + numpy and polymer_protocol resolve):
    cd /Users/zbb2/Desktop/polymer-claims \
      && uv run --project . python viewer/scripts/make_spectral_timeline.py
"""
from __future__ import annotations

import json
from pathlib import Path

from polymer_protocol import (
    Layout,
    TimelineFrame,
    TopologyTimeline,
    export_topology,
    frame_stats,
    n_licensed,
)

from polymer_claims._synthetic_corpus import growing_cluster0_corpora
from polymer_claims.embedding import procrustes_align, spectral_layout

_OUT = Path(__file__).resolve().parents[1] / "public" / "sample-spectral-timeline.json"


def main() -> None:
    corpora = growing_cluster0_corpora()
    frames: list[TimelineFrame] = []
    prev_spectral: dict[str, tuple] = {}
    # Match the canonical frame_stats convention (NodeRunner.__init__ / export_timeline): seed
    # licensed_prev from the frame-0 corpus and report n_newly_licensed=0 for frame 0.
    licensed_prev = n_licensed(corpora[0])
    for i, corpus in enumerate(corpora):
        aligned = procrustes_align(prev_spectral, spectral_layout(corpus))
        prev_spectral = aligned
        topo = export_topology(corpus, layout=Layout.FORCE_DIRECTED, positions=aligned)
        licensed_now = n_licensed(corpus)
        n_newly = 0 if i == 0 else max(0, licensed_now - licensed_prev)
        stats = frame_stats(
            corpus,
            topo,
            cycle_index=i,
            n_frontier=0,
            n_added=0,
            n_newly_licensed=n_newly,
        )
        licensed_prev = licensed_now
        frames.append(TimelineFrame(topology=topo, stats=stats))

    timeline = TopologyTimeline(frames=tuple(frames), n_cycles=len(frames) - 1)
    _OUT.write_text(json.dumps(timeline.model_dump(mode="json"), indent=2) + "\n")
    last = timeline.frames[-1].topology
    print(f"wrote {_OUT} ({len(timeline.frames)} frames, last layout={last.layout_id}, "
          f"{len(last.nodes)} nodes)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script to generate the artifact**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . python viewer/scripts/make_spectral_timeline.py`
Expected: prints `wrote .../sample-spectral-timeline.json (5 frames, last layout=external:spectral-v1, 8 nodes)` and the JSON file exists.

- [ ] **Step 3: Sanity-check the artifact round-trips as a TopologyTimeline and grows smoothly**

Run:
```bash
cd /Users/zbb2/Desktop/polymer-claims && uv run --project . python -c "
import json
from polymer_protocol import TopologyTimeline
d = json.load(open('viewer/public/sample-spectral-timeline.json'))
tl = TopologyTimeline.model_validate(d)
assert tl.frames[-1].topology.layout_id == 'external:spectral-v1'
# node counts grow monotonically (smooth reveal), and the last frame has the full cluster
counts = [len(f.topology.nodes) for f in tl.frames]
assert counts == sorted(counts) and counts[-1] == 8, counts
print('ok', len(tl.frames), 'frames', counts)
"
```
Expected: `ok 5 frames [4, 5, 6, 7, 8]`.

- [ ] **Step 4: Commit**

```bash
cd /Users/zbb2/Desktop/polymer-claims
git add viewer/scripts/make_spectral_timeline.py viewer/public/sample-spectral-timeline.json
git commit -m "feat(viewer): spectral timeline demo artifact (smooth Procrustes-aligned growth)"
```

---

## Task 5: Full green gate (AC#6)

**Files:** none (verification only)

- [ ] **Step 1: Run the full check suite**

Run: `cd /Users/zbb2/Desktop/polymer-claims && ./scripts/check-all.sh`
Expected: ALL GREEN (protocol untouched + numpy-free; `node.py` base import numpy-free; Corpus = 4; force byte-identical; spectral live).

- [ ] **Step 2: If anything is red, stop and report**

Do not paper over a failure. If `check-all.sh` reports a regression, surface the exact failing command + output before any further change.

---

## Acceptance criteria → task map

1. `procrustes_align` recovers a known rotation+reflection within 1e-6 → **Task 1** (`test_procrustes_align_recovers_rotation_and_reflection`).
2. Anti-thrash: aligned per-node displacement bounded and strictly smaller than raw-spectral → **Task 2** (`test_procrustes_kills_eigenbasis_thrash_on_growing_component`, over the growing ≥4-component fixture, with a non-vacuous `raw_max > 0.5` guard and an `aligned_max < 0.75 * raw_max` margin). See the design note for why this uses the growing-component corpus, not the default seed.
3. Spectral frame carries `layout_id == "external:spectral-v1"` + non-origin positions; corpus evolves identically → **Task 2** (`test_spectral_nodeRunner_frame_is_external_and_nonorigin`, over the default seed — the integration path).
4. `layout="force"` byte-identical to current behaviour → **Task 2** (existing `test_node.py` tests pinned to `layout="force"` + `test_force_layout_is_fruchterman_reingold`).
5. `serve --layout spectral`/`force` constructs the matching runner → **Task 3** (`test_serve_layout_threads_into_runner`, `test_serve_layout_defaults_to_spectral`).
6. `node.py` base import numpy-free; protocol untouched; Corpus = 4; `check-all.sh` ALL GREEN → **Task 2 Step 11** (existing `test_node_import_stays_numpy_free`) + **Task 5**.

## Invariants preserved (spec §"Invariants")

- Protocol untouched + numpy-free: no protocol files modified; the `positions=` seam already existed.
- `node.py` base import numpy-free: embedder lazy-imported inside `_spectral_positions` only (guarded by `test_node_import_stays_numpy_free`).
- `layout="force"` byte-identical: `_layout_topology` force branch passes `seed_positions=self.prev_positions` (`{}`≡`None` at frame 0); force path otherwise untouched.
- Spectral positions deterministic: sign-canonicalized eigenmap + Procrustes SVD + 6dp round.
