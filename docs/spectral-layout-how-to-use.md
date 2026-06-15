# Spectral layout — How to use

The live claim universe can be laid out two ways. **`spectral`** (default) places each claim by the
signed-Laplacian eigenmap of the typed-edge graph (meaningful relational positions), Procrustes-aligned
frame-to-frame so the universe grows smoothly. **`force`** is the legacy id-hash Fruchterman-Reingold layout.

## Requirements

- Spectral needs numpy, behind the umbrella **`[embed]`** extra: `pip install 'polymer-claims[embed]'`
  (the dev env has it). Without it, spectral **gracefully falls back to force** (warns once); nothing breaks.
- The grammar/protocol core stays numpy-free — the embedder is lazy-imported only when a spectral frame is built.

## Live node (CLI)

```bash
polymer-claims serve --layout spectral   # default — the eigenmap, Procrustes-aligned
polymer-claims serve --layout force      # legacy Fruchterman-Reingold (byte-identical to before)
```

The viewer renders whatever positions the SSE frames carry; no viewer flag is needed.

## Programmatic (NodeRunner)

```python
from polymer_claims.node import NodeRunner

runner = NodeRunner.from_seed(corpus, layout="spectral")  # or layout="force"
for _ in range(n):
    runner.tick()
timeline = runner.snapshot()        # TopologyTimeline; spectral frames carry layout_id "external:spectral-v1"
```

## Embedding functions directly

```python
from polymer_claims.embedding import spectral_layout, procrustes_align

raw   = spectral_layout(corpus)              # dict[claim_id -> (x, y, z)], deterministic, 6dp
final = procrustes_align(prev_positions, raw)  # rotate/reflect `raw` onto the previous frame
```

`spectral_layout` is a pure snapshot. `procrustes_align` is what makes a *sequence* of snapshots evolve
smoothly — call it each frame with the previous **displayed** positions as `prev`. (`NodeRunner` does this
for you via its internal `_prev_spectral` chain.)

## Demo timeline + viewer

```bash
# regenerate the smooth-growth sample artifact (viewer/public/sample-spectral-timeline.json)
uv run --project . python viewer/scripts/make_spectral_timeline.py
```

To watch it: serve the JSON as the viewer's timeline (the loader reads `/sample-timeline.json`) and open
the viewer — the transport bar scrubs/plays the frames; the universe grows node-by-node without spinning.

## When spectral helps (and when it won't)

- **Helps** when the corpus has a **connected component of ≥4 claims** linked by typed edges
  (entails / equivalence / evidence / defeat). That is where the eigenmap is meaningful and where the
  alignment kills the frame-to-frame thrash.
- **Won't look smoother** on tiny/disconnected corpora (every claim in its own ≤3-node group). There the
  eigenmap degenerates to a deterministic id-hash placement on a lattice, and the only motion is lattice
  re-indexing as components appear — which no global rotation can absorb. Use `--layout force` there.

## Guarantees

- **Deterministic** — same corpus sequence → byte-identical positions (sign-canonicalized eigenmap + SVD + 6dp).
- **`layout="force"` is byte-identical** to the pre-feature behavior.
- **Protocol untouched / numpy-free**; positions are injected through the existing
  `export_topology(positions=)` seam (`layout_id="external:spectral-v1"`).
