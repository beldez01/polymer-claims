# Relational Graph Embedding (v1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each claim a *meaningful* 3D position — a deterministic signed-Laplacian eigenmap over the corpus's typed conceptual edges — so the viewer shows conceptual structure, not an id-hash force layout.

**Architecture:** Umbrella-side `numpy` embedding (`embedding.py`) computes positions from a `Corpus`; one additive `positions=` param on protocol's `export_topology` injects them (protocol stays numpy-free); a harness script writes a `sample-topology-spectral.json` the existing viewer renders; a planted K-cluster synthetic corpus + a silhouette-style separation test make "meaningful" objectively testable.

**Tech Stack:** Python 3.12, numpy (new umbrella dep), Pydantic v2, pytest, uv, ruff. Determinism via `numpy.linalg.eigh` + eigenvector sign canonicalization + rounding.

**Spec:** `docs/superpowers/specs/2026-06-12-relational-graph-embedding-design.md`
**Branch:** continue on `feat/m1-structural-equivalence-status` (work is stacked; nothing merged).
**Umbrella tests run from repo root:** `uv run --project . pytest tests/ -q`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `protocol/src/polymer_protocol/topology.py` | `export_topology` | Modify: add optional `positions=` override (numpy-free) |
| `protocol/tests/test_topology.py` (or new `test_topology_positions.py`) | the new seam | Test |
| `pyproject.toml` (umbrella) | deps | Modify: add `numpy` ( `[embed]` extra + dev group) |
| `src/polymer_claims/embedding.py` | the embedding: graph build + signed-Laplacian eigenmap | Create |
| `src/polymer_claims/_synthetic_corpus.py` | planted K-cluster corpus shared by harness + tests | Create |
| `tests/test_embedding_graph.py` | typed-weight graph construction | Create |
| `tests/test_embedding.py` | success criteria: separation / polarity / determinism / degenerate | Create |
| `viewer/scripts/make_spectral_sample.py` | experiment harness → `sample-topology-spectral.json` | Create |
| `viewer/public/sample-topology-spectral.json` | generated output | Create (generated) |

`grammar/` is untouched. `embedding.py` is **not** re-exported from `src/polymer_claims/__init__.py` (that would pull numpy into the base import); import it as `from polymer_claims.embedding import spectral_layout`.

---

## Task 1: Protocol seam — `export_topology(positions=...)`

**Files:**
- Modify: `protocol/src/polymer_protocol/topology.py:310-339`
- Test: `protocol/tests/test_topology_positions.py` (new)

- [ ] **Step 1: Write the failing test**

Create `protocol/tests/test_topology_positions.py`:

```python
from polymer_grammar import Status
from polymer_protocol.corpus import Corpus
from polymer_protocol.topology import Layout, export_topology
from tests.conftest import make_claim  # existing helper in protocol/tests/conftest.py


def _corpus():
    a = make_claim("a", status=Status.PENDING)
    b = make_claim("b", status=Status.PENDING)
    return Corpus(claims=(a, b))


def test_positions_override_used_verbatim():
    corpus = _corpus()
    pos = {"a": (0.1, 0.2, 0.3), "b": (-0.4, -0.5, -0.6)}
    export = export_topology(corpus, layout=Layout.FORCE_DIRECTED, positions=pos)
    by_id = {n.id: n.position for n in export.nodes}
    assert by_id["a"] == (0.1, 0.2, 0.3)
    assert by_id["b"] == (-0.4, -0.5, -0.6)
    assert export.layout_id == "external:spectral-v1"


def test_missing_position_falls_back_to_origin():
    corpus = _corpus()
    export = export_topology(corpus, layout=Layout.FORCE_DIRECTED, positions={"a": (1.0, 1.0, 1.0)})
    by_id = {n.id: n.position for n in export.nodes}
    assert by_id["b"] == (0.0, 0.0, 0.0)


def test_no_positions_is_unchanged_force_directed():
    corpus = _corpus()
    e1 = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
    e2 = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
    assert e1 == e2  # still deterministic, FR path untouched
    assert e1.layout_id.startswith("fruchterman-reingold")
```

(If `make_claim` in `protocol/tests/conftest.py` requires extra args, mirror its usage from an existing test such as `protocol/tests/test_canonicalize.py`.)

- [ ] **Step 2: Run to confirm failure**

Run: `cd /Users/zbb2/Desktop/polymer-claims/protocol && uv run pytest tests/test_topology_positions.py -q`
Expected: FAIL — `export_topology() got an unexpected keyword argument 'positions'`.

- [ ] **Step 3: Add the param**

In `protocol/src/polymer_protocol/topology.py`, change the `export_topology` signature and body:

```python
def export_topology(
    corpus: Corpus,
    *,
    layout: Layout,
    seed_positions: dict[str, tuple[float, float, float]] | None = None,
    positions: dict[str, tuple[float, float, float]] | None = None,
) -> TopologyExport:
    """Pure, deterministic corpus → TopologyExport.

    Layout.NONE zeroes every position; FORCE_DIRECTED runs the seeded Fruchterman-Reingold layout.
    `positions` (when supplied) overrides both: each node takes its coordinate from the dict (a
    missing id → origin), `layout_id="external:spectral-v1"`, and `layout`/`seed_positions` are
    ignored — this is the seam an external embedder (e.g. the umbrella spectral layout) injects
    through. Nodes/edges/clusters are sorted for byte-stable output.

    `seed_positions` warm-starts FORCE_DIRECTED from a prior frame's positions; the default-None
    path leaves the no-seed output byte-identical. Determinism: identical inputs → identical output.
    """
    edges = _extract_edges(corpus)
    clusters = _extract_clusters(corpus)
    node_ids = [c.id for c in corpus.claims]

    if positions is not None:
        layout_positions = {cid: positions.get(cid, (0.0, 0.0, 0.0)) for cid in node_ids}
        layout_id = "external:spectral-v1"
    elif layout is Layout.NONE:
        layout_positions = {cid: (0.0, 0.0, 0.0) for cid in node_ids}
        layout_id = "none"
    else:
        layout_positions, layout_id = _force_directed_layout(node_ids, edges, seed_positions)

    nodes = _extract_nodes(corpus, layout_positions)
    return TopologyExport(
        nodes=nodes, edges=edges, clusters=clusters, layout_id=layout_id
    )
```

- [ ] **Step 4: Run tests**

Run: `cd protocol && uv run pytest tests/test_topology_positions.py tests/test_topology.py -q && uv run ruff check src tests`
Expected: PASS (new tests + every existing topology test — proving the no-`positions` path is unchanged); ruff clean.

- [ ] **Step 5: Commit**

```bash
git add protocol/src/polymer_protocol/topology.py protocol/tests/test_topology_positions.py
git commit -m "feat(protocol): export_topology positions= override seam (numpy-free)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2: numpy dep + typed-weight graph construction

**Files:**
- Modify: `pyproject.toml`
- Create: `src/polymer_claims/embedding.py` (graph-build portion this task)
- Test: `tests/test_embedding_graph.py`

- [ ] **Step 1: Add numpy to the umbrella deps**

In `pyproject.toml`: add an optional extra and a dev-group entry (keeps the base wheel numpy-free; tests/check-all get it via the dev group). Under `[project.optional-dependencies]` add:

```toml
embed = ["numpy>=1.26"]
```

And add `"numpy>=1.26"` to the `dev` list in `[dependency-groups]`. Then run `uv sync` so the env has numpy:

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv sync`

- [ ] **Step 2: Write the failing test**

Create `tests/test_embedding_graph.py`:

```python
from __future__ import annotations

from polymer_claims.embedding import KIND_WEIGHT, build_graph
from polymer_claims._synthetic_corpus import planted_corpus


def test_kind_weights_match_spec():
    assert KIND_WEIGHT["equivalence"] == 1.0
    assert KIND_WEIGHT["entails"] == 0.9
    assert KIND_WEIGHT["evidence_for"] == 0.8
    assert KIND_WEIGHT["undermine"] == KIND_WEIGHT["undercut"] == 0.5
    assert KIND_WEIGHT["reclassify"] == KIND_WEIGHT["reinterpret"] == 0.5
    assert KIND_WEIGHT["rebut"] == 0.4


def test_build_graph_weights_and_symmetry():
    corpus = planted_corpus()
    node_ids, W, polar = build_graph(corpus)
    assert set(node_ids) == {c.id for c in corpus.claims}
    # every weight is a known kind weight; keys are unordered pairs (frozensets)
    for key, w in W.items():
        assert isinstance(key, frozenset) and len(key) == 2
        assert w in set(KIND_WEIGHT.values())
    # the planted opposite-direction rebut pair is flagged polar
    assert any(len(p) == 2 for p in polar)


def test_polar_only_on_opposite_direction_rebut():
    corpus = planted_corpus()
    _, _, polar = build_graph(corpus)
    # polar pairs are a subset of the edge set, never empty for the planted corpus
    assert polar  # the planted corpus includes a positive-vs-negative rebut
```

(This test imports `planted_corpus` from Task 4's module; if Task 4 isn't done yet, this task may be implemented after Task 4, or stub `planted_corpus` minimally first. Recommended order: do Task 4's `_synthetic_corpus.py` builder before this test runs green. The graph CODE below has no dependency on the corpus builder.)

- [ ] **Step 3: Write the graph-build code**

Create `src/polymer_claims/embedding.py` (graph portion; the eigenmap is added in Task 3):

```python
"""Relational graph embedding (CES viz v1): a deterministic signed-Laplacian eigenmap over the
corpus's typed conceptual edges, giving each claim a MEANINGFUL 3D position (vs the id-hash force
layout). Umbrella/impure (numpy). The grammar/protocol core never imports this; it is consumed by
the viewer harness and tests. NOT re-exported from polymer_claims.__init__ (keeps base import
numpy-free). See docs/specs/2026-06-12-relational-graph-embedding-design.md.
"""
from __future__ import annotations

from polymer_grammar import Direction
from polymer_protocol import Layout, export_topology
from polymer_protocol.corpus import Corpus

# Edge kind -> attraction weight (the stated conceptual commitment; see spec §2). incompatible_with
# is deferred to v1.1 (not in the resolved topology edge export yet).
KIND_WEIGHT: dict[str, float] = {
    "equivalence": 1.0,
    "entails": 0.9,
    "evidence_for": 0.8,
    "undermine": 0.5,
    "undercut": 0.5,
    "reclassify": 0.5,
    "reinterpret": 0.5,
    "rebut": 0.4,
}
RHO = 0.3  # polarity repulsion for an opposite-direction rebut pair


def build_graph(
    corpus: Corpus,
) -> tuple[list[str], dict[frozenset[str], float], set[frozenset[str]]]:
    """Return (sorted node ids, weighted adjacency W keyed by unordered pair, polar pair set).

    Edges are sourced from the resolved topology export (entails ∪ equivalence ∪ defeat) so the
    embedding matches the graph the viewer draws. A rebut between opposite-`direction` conclusions
    is flagged polar (gets a repulsion in the eigenmap)."""
    export = export_topology(corpus, layout=Layout.NONE)
    node_ids = sorted(c.id for c in corpus.claims)
    valid = set(node_ids)
    direction_by_id = {
        c.id: (c.conclusion.direction if c.conclusion is not None else None)
        for c in corpus.claims
    }

    W: dict[frozenset[str], float] = {}
    polar: set[frozenset[str]] = set()
    for e in export.edges:
        if e.source == e.target or e.source not in valid or e.target not in valid:
            continue  # skip self-loops and synthetic ':'-source nodes
        w = KIND_WEIGHT.get(e.kind)
        if w is None:
            continue
        key = frozenset((e.source, e.target))
        W[key] = max(W.get(key, 0.0), w)  # strongest relation wins; weak doesn't dilute
        if e.kind == "rebut":
            ds, dt = direction_by_id.get(e.source), direction_by_id.get(e.target)
            if {ds, dt} == {Direction.POSITIVE, Direction.NEGATIVE}:
                polar.add(key)
    return node_ids, W, polar
```

- [ ] **Step 4: Run tests**

Run: `uv run --project . pytest tests/test_embedding_graph.py -q` (after Task 4's `_synthetic_corpus.py` exists) and `uv run --project . ruff check src tests`
Expected: PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/polymer_claims/embedding.py tests/test_embedding_graph.py
git commit -m "feat(umbrella): typed-weight graph construction for the relational embedding (numpy dep)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3: The signed-Laplacian eigenmap (`spectral_layout`)

**Files:**
- Modify: `src/polymer_claims/embedding.py` (append the embedding)
- Test: `tests/test_embedding.py` (determinism + degenerate portion this task; success metrics in Task 4)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_embedding.py`:

```python
from __future__ import annotations

import math

from polymer_claims.embedding import spectral_layout
from polymer_claims._synthetic_corpus import planted_corpus
from polymer_protocol.corpus import Corpus


def test_spectral_layout_is_deterministic():
    corpus = planted_corpus()
    a = spectral_layout(corpus)
    b = spectral_layout(corpus)
    assert a == b  # byte-identical (sign-canonicalized + rounded)


def test_every_claim_gets_a_finite_position():
    corpus = planted_corpus()
    pos = spectral_layout(corpus)
    assert set(pos) == {c.id for c in corpus.claims}
    for xyz in pos.values():
        assert len(xyz) == 3
        assert all(math.isfinite(v) for v in xyz)


def test_empty_corpus_returns_empty():
    assert spectral_layout(Corpus(claims=())) == {}


def test_positions_are_in_unit_cube():
    pos = spectral_layout(planted_corpus())
    for xyz in pos.values():
        assert all(-1.0001 <= v <= 1.0001 for v in xyz)
```

- [ ] **Step 2: Run to confirm failure**

Run: `uv run --project . pytest tests/test_embedding.py -q`
Expected: FAIL — `ImportError: cannot import name 'spectral_layout'`.

- [ ] **Step 3: Append the eigenmap implementation**

Append to `src/polymer_claims/embedding.py` (add `import hashlib`, `import math`, `import numpy as np` at the top):

```python
_FALLBACK_RADIUS = 0.15
_CELL_SPACING = 2.5


def _hash_ball(node_id: str, radius: float = _FALLBACK_RADIUS) -> tuple[float, float, float]:
    """Deterministic position in a small ball from the id hash (for tiny/isolated components)."""
    digest = hashlib.sha256(node_id.encode("utf-8")).digest()
    out = []
    for i in range(3):
        u = int.from_bytes(digest[i * 8 : (i + 1) * 8], "big") / float(2**64)
        out.append(radius * (2.0 * u - 1.0))
    return (out[0], out[1], out[2])


def _components(node_ids: list[str], W: dict[frozenset[str], float]) -> list[list[str]]:
    adj: dict[str, set[str]] = {n: set() for n in node_ids}
    for key in W:
        a, b = tuple(key)
        adj[a].add(b)
        adj[b].add(a)
    seen: set[str] = set()
    comps: list[list[str]] = []
    for n in node_ids:
        if n in seen:
            continue
        stack, comp = [n], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack.extend(adj[x] - seen)
        comps.append(sorted(comp))
    return comps


def _embed_component(
    comp: list[str], W: dict[frozenset[str], float], polar: set[frozenset[str]]
) -> dict[str, tuple[float, float, float]]:
    n = len(comp)
    if n < 4:
        return {nid: _hash_ball(nid) for nid in comp}
    idx = {nid: i for i, nid in enumerate(comp)}
    A = np.zeros((n, n))
    for key, w in W.items():
        a, b = tuple(key)
        if a in idx and b in idx:
            val = w - (RHO if key in polar else 0.0)
            A[idx[a], idx[b]] = val
            A[idx[b], idx[a]] = val
    deg = np.abs(A).sum(axis=1)
    deg[deg == 0] = 1.0
    dinv = 1.0 / np.sqrt(deg)
    L = np.eye(n) - (dinv[:, None] * A * dinv[None, :])
    _, vecs = np.linalg.eigh(L)  # ascending eigenvalues; columns are eigenvectors
    coords = vecs[:, 1:4].copy()  # skip the trivial null component, take the next 3
    for k in range(coords.shape[1]):
        col = coords[:, k]
        j = int(np.argmax(np.abs(col)))  # lowest index on ties → deterministic sign
        if col[j] < 0:
            coords[:, k] = -col
        m = np.abs(coords[:, k]).max()
        if m > 0:
            coords[:, k] = coords[:, k] / m
    return {nid: tuple(float(v) for v in coords[idx[nid]]) for nid in comp}


def spectral_layout(corpus: Corpus) -> dict[str, tuple[float, float, float]]:
    """Deterministic 3D position per claim from the typed-edge signed-Laplacian eigenmap.

    Per connected component (so unrelated subgraphs separate); components placed on a deterministic
    lattice; sign-canonicalized and rounded → byte-stable. Empty corpus → {}."""
    node_ids, W, polar = build_graph(corpus)
    if not node_ids:
        return {}
    comps = sorted(_components(node_ids, W), key=lambda c: c[0])
    side = max(1, math.ceil(len(comps) ** (1.0 / 3.0)))
    raw: dict[str, tuple[float, float, float]] = {}
    for ci, comp in enumerate(comps):
        local = _embed_component(comp, W, polar)
        gx, gy, gz = ci % side, (ci // side) % side, ci // (side * side)
        ox = (gx - (side - 1) / 2.0) * _CELL_SPACING
        oy = (gy - (side - 1) / 2.0) * _CELL_SPACING
        oz = (gz - (side - 1) / 2.0) * _CELL_SPACING
        for nid, (x, y, z) in local.items():
            raw[nid] = (x + ox, y + oy, z + oz)
    scale = max((abs(v) for xyz in raw.values() for v in xyz), default=1.0) or 1.0
    return {nid: tuple(round(v / scale, 6) for v in xyz) for nid, xyz in raw.items()}
```

- [ ] **Step 4: Run tests**

Run: `uv run --project . pytest tests/test_embedding.py -q && uv run --project . ruff check src tests`
Expected: PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/embedding.py tests/test_embedding.py
git commit -m "feat(umbrella): signed-Laplacian eigenmap spectral_layout (per-component, deterministic)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4: Planted synthetic corpus + the success-criteria tests

**Files:**
- Create: `src/polymer_claims/_synthetic_corpus.py`
- Modify: `tests/test_embedding.py` (append the success metrics)
- Test: the appended metrics

- [ ] **Step 1: Build the planted corpus (model it on `viewer/scripts/make_sample.py`)**

Create `src/polymer_claims/_synthetic_corpus.py` exporting `planted_corpus() -> Corpus`. Use the EXACT grammar/protocol constructors shown in `viewer/scripts/make_sample.py` (Claim, Proposition with `direction`, PatternRef, CategoricalLeaf, EquivalenceClaim, DefeatEdge/DefeatEdgeKind, NeighborEdge/NeighborEdgeKind, Corpus). The builder is **deterministic, no RNG**, and MUST produce, by construction:

- **3 planted clusters**, ~8 claims each, on 3 distinct subjects/estimands (e.g. cluster ids `c0_*`, `c1_*`, `c2_*`).
- **Dense intra-cluster edges:** within each cluster, link claims with `ENTAILS` (proposition neighborhood) and `evidence_for` defeat edges, plus ≥1 `equivalence` edge per cluster between two near-duplicate claims.
- **Sparse inter-cluster edges:** at most 1 cross-cluster edge total.
- **A polar probe:** in cluster 0, two claims whose conclusions have **opposite `direction`** (POSITIVE vs NEGATIVE) linked by a `rebut` defeat edge.
- **An equivalence probe:** record which two claim ids are the equivalence pair (expose a module constant e.g. `EQUIV_PAIR: tuple[str, str]`, `POLAR_PAIR: tuple[str, str]`, and `CLUSTERS: dict[str, list[str]]` so the tests can assert against the ground truth without guessing).
- **2–3 isolated claims** with no edges (exercise the fallback).

Expose: `planted_corpus()`, `CLUSTERS`, `EQUIV_PAIR`, `POLAR_PAIR`, `ISOLATED` (list of ids).

(If a constructor signature is unclear, copy its exact usage from `viewer/scripts/make_sample.py`, which builds a working multi-cluster corpus with every edge type.)

- [ ] **Step 2: Write the failing success tests** — append to `tests/test_embedding.py`:

```python
import itertools

from polymer_claims._synthetic_corpus import (
    CLUSTERS, EQUIV_PAIR, POLAR_PAIR, planted_corpus,
)


def _dist(p, q):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p, q)))


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def test_clusters_separate_intra_below_inter():
    pos = spectral_layout(planted_corpus())
    intra, inter = [], []
    for cl, ids in CLUSTERS.items():
        for a, b in itertools.combinations(ids, 2):
            intra.append(_dist(pos[a], pos[b]))
    cluster_lists = list(CLUSTERS.values())
    for i in range(len(cluster_lists)):
        for j in range(i + 1, len(cluster_lists)):
            for a in cluster_lists[i]:
                for b in cluster_lists[j]:
                    inter.append(_dist(pos[a], pos[b]))
    mean_intra, mean_inter = _mean(intra), _mean(inter)
    # silhouette-style separation: clusters are tighter than the gaps between them
    assert mean_intra < mean_inter
    assert (mean_inter - mean_intra) / mean_inter > 0.25


def test_polar_pair_near_but_not_coincident():
    pos = spectral_layout(planted_corpus())
    d_polar = _dist(pos[POLAR_PAIR[0]], pos[POLAR_PAIR[1]])
    # near: closer than a typical cross-cluster gap
    inter = []
    cluster_lists = list(CLUSTERS.values())
    for a in cluster_lists[0]:
        for b in cluster_lists[1]:
            inter.append(_dist(pos[a], pos[b]))
    assert 0.0 < d_polar < _mean(inter)


def test_equivalence_pair_is_very_close():
    pos = spectral_layout(planted_corpus())
    d_eq = _dist(pos[EQUIV_PAIR[0]], pos[EQUIV_PAIR[1]])
    # the equivalence pair is the tightest relation: closer than the polar (rebut) pair
    d_polar = _dist(pos[POLAR_PAIR[0]], pos[POLAR_PAIR[1]])
    assert d_eq < d_polar
```

- [ ] **Step 3: Run — confirm the metrics drive the corpus to be right**

Run: `uv run --project . pytest tests/test_embedding.py tests/test_embedding_graph.py -q`
Expected: PASS. If `test_clusters_separate_intra_below_inter` fails, the planted corpus's intra-edges are too sparse or inter-edges too many — adjust the corpus density (NOT the test threshold) until the hypothesis-style separation holds. This is the experiment's pass/fail line; tune the corpus, not the metric. If it cannot be made to pass with reasonable density, STOP and report — that is a real finding about the embedding, not a test bug.

- [ ] **Step 4: Run ruff**

Run: `uv run --project . ruff check src tests` → clean.

- [ ] **Step 5: Commit**

```bash
git add src/polymer_claims/_synthetic_corpus.py tests/test_embedding.py
git commit -m "test(umbrella): planted K-cluster corpus + separation/polarity/equivalence metrics (embedding)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5: Harness, sample render, verification, docs

**Files:**
- Create: `viewer/scripts/make_spectral_sample.py`
- Create (generated): `viewer/public/sample-topology-spectral.json`
- Modify: `docs/superpowers/CONTINUE.md`, the credibility-arc roadmap (note: embedding is a separate viz arc — add a brief pointer, do not overwrite CES entries)

- [ ] **Step 1: Write the harness**

Create `viewer/scripts/make_spectral_sample.py` (mirrors `make_sample.py` but injects spectral positions):

```python
"""Generate a relational-embedding sample TopologyExport for the viewer.

Builds the planted synthetic corpus, computes the signed-Laplacian spectral layout, and writes a
TopologyExport (positions = the embedding) to viewer/public/sample-topology-spectral.json.

RUN (from the UMBRELLA env so polymer_claims + numpy and polymer_protocol resolve):
    cd /Users/zbb2/Desktop/polymer-claims \
      && uv run --project . python viewer/scripts/make_spectral_sample.py
"""
from __future__ import annotations

import json
from pathlib import Path

from polymer_claims._synthetic_corpus import planted_corpus
from polymer_claims.embedding import spectral_layout
from polymer_protocol import Layout, export_topology

_OUT = Path(__file__).resolve().parents[1] / "public" / "sample-topology-spectral.json"


def main() -> None:
    corpus = planted_corpus()
    positions = spectral_layout(corpus)
    export = export_topology(corpus, layout=Layout.FORCE_DIRECTED, positions=positions)
    _OUT.write_text(json.dumps(export.model_dump(mode="json"), indent=2) + "\n")
    print(f"wrote {_OUT} ({len(export.nodes)} nodes, layout={export.layout_id})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate the sample**

Run: `cd /Users/zbb2/Desktop/polymer-claims && uv run --project . python viewer/scripts/make_spectral_sample.py`
Expected: prints `wrote .../sample-topology-spectral.json (N nodes, layout=external:spectral-v1)`. Confirm the file exists and is valid JSON with `nodes[].position` populated (not all zeros).

- [ ] **Step 3: Guard the generated sample with a test**

Append to `tests/test_embedding.py`:

```python
def test_spectral_sample_file_is_valid_and_nontrivial():
    import json
    from pathlib import Path
    from polymer_protocol.topology import TopologyExport

    p = Path(__file__).resolve().parents[1] / "viewer" / "public" / "sample-topology-spectral.json"
    export = TopologyExport.model_validate(json.loads(p.read_text()))
    assert export.layout_id == "external:spectral-v1"
    assert len(export.nodes) > 10
    # positions are real (not the all-origin fallback)
    assert any(any(v != 0.0 for v in n.position) for n in export.nodes)
```

Run: `uv run --project . pytest tests/test_embedding.py -q` → PASS.

- [ ] **Step 4: Full verification**

Run:
```bash
uv run --project . pytest tests/ -q && uv run --project . ruff check src tests
cd /Users/zbb2/Desktop/polymer-claims && bash scripts/check-all.sh
```
Expected: all umbrella tests green; ruff clean; `check-all.sh` → `ALL GREEN` (grammar/protocol/umbrella/isolation/viewer build — confirms the protocol seam didn't disturb anything and the viewer still builds).

- [ ] **Step 5: Docs + commit**

Add a dated `✅ RELATIONAL EMBEDDING v1 DONE` note to `docs/superpowers/CONTINUE.md` recording: the hypothesis tested (edges carry conceptual structure), `embedding.spectral_layout` (signed-Laplacian, per-component, deterministic), the `export_topology(positions=)` seam, the planted-corpus separation result (quote the silhouette margin if notable), the `sample-topology-spectral.json` to load in the viewer, and that this is a NEW viz arc (not part of CES). Add a one-line pointer in the credibility-arc roadmap's deferred/related section. Do NOT alter CES or M1 entries.

```bash
git add viewer/scripts/make_spectral_sample.py viewer/public/sample-topology-spectral.json \
        tests/test_embedding.py docs/superpowers/CONTINUE.md \
        docs/superpowers/roadmaps/2026-06-11-credibility-arc-roadmap.md
git commit -m "feat(viewer): relational embedding sample + harness; CONTINUE (embedding v1 done)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- §1 umbrella embedding + protocol `positions=` seam → Tasks 1–3. ✓
- §2 typed-weight graph from resolved topology edges + rebut polarity → Task 2. ✓
- §3 per-component signed-Laplacian eigenmap, sign canon, fallback, lattice → Task 3. ✓
- §4 protocol seam additive/back-compat → Task 1 (incl. byte-identical no-positions test). ✓
- §5 harness + synthetic corpus + view → Tasks 4, 5. ✓
- §6 success tests (separation / polarity / equivalence / determinism / degenerate / back-compat / check-all) → Tasks 1, 3, 4, 5. ✓
- §7 numpy on umbrella only → Task 2 (extra + dev group; base import numpy-free, embedding not re-exported). ✓
- §8 scope fences (no UMAP, no content, static only) → nothing in the plan adds them. ✓

**Placeholder scan:** the only non-literal step is Task 4's corpus builder, which is specified by exact required output properties + ground-truth constants + a working template (`make_sample.py`) and pinned by the Task-4 metric tests — not a placeholder, an executable contract.

**Type consistency:** `build_graph` returns `(list[str], dict[frozenset,float], set[frozenset])` and is consumed identically in Task 3. `spectral_layout(corpus) -> dict[str, tuple]` matches its consumers in Tasks 4–5. `KIND_WEIGHT`/`RHO` names consistent across tasks. `planted_corpus()`/`CLUSTERS`/`EQUIV_PAIR`/`POLAR_PAIR` names consistent between Task 4 definition and its tests. `export_topology(..., positions=)` signature consistent across Tasks 1, 5.

**Ordering note:** Task 2's graph test and Task 3's tests import `planted_corpus` (Task 4). Implement Task 1, then Task 4's `_synthetic_corpus.py` builder, then Tasks 2 and 3, then Task 4's metric tests, then Task 5 — OR keep plan order and let the importing tests stay red until Task 4 lands. The subagent controller should sequence so each task ends green; the cleanest is **1 → 4(builder only) → 2 → 3 → 4(metrics) → 5**.
