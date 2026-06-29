# Spectral layout

The live claim universe can be laid out two ways. **`spectral`** (default) places each claim by the
signed-Laplacian eigenmap of the typed-edge graph (meaningful relational positions), Procrustes-aligned
frame-to-frame so the universe grows smoothly. **`force`** is the legacy id-hash Fruchterman-Reingold layout.

---

## Part 1 — How to use

### Requirements

- Spectral needs numpy, behind the umbrella **`[embed]`** extra: `pip install 'polymer-claims[embed]'`
  (the dev env has it). Without it, spectral **gracefully falls back to force** (warns once); nothing breaks.
- The grammar/protocol core stays numpy-free — the embedder is lazy-imported only when a spectral frame is built.

### Live node (CLI)

```bash
polymer-claims serve --layout spectral   # default — the eigenmap, Procrustes-aligned
polymer-claims serve --layout force      # legacy Fruchterman-Reingold (byte-identical to before)
```

The viewer renders whatever positions the SSE frames carry; no viewer flag is needed.

### Programmatic (NodeRunner)

```python
from polymer_claims.node import NodeRunner

runner = NodeRunner.from_seed(corpus, layout="spectral")  # or layout="force"
for _ in range(n):
    runner.tick()
timeline = runner.snapshot()        # TopologyTimeline; spectral frames carry layout_id "external:spectral-v1"
```

### Embedding functions directly

```python
from polymer_claims.embedding import spectral_layout, procrustes_align

raw   = spectral_layout(corpus)              # dict[claim_id -> (x, y, z)], deterministic, 6dp
final = procrustes_align(prev_positions, raw)  # rotate/reflect `raw` onto the previous frame
```

`spectral_layout` is a pure snapshot. `procrustes_align` is what makes a *sequence* of snapshots evolve
smoothly — call it each frame with the previous **displayed** positions as `prev`. (`NodeRunner` does this
for you via its internal `_prev_spectral` chain.)

### Demo timeline + viewer

```bash
# regenerate the smooth-growth sample artifact (viewer/public/sample-spectral-timeline.json)
uv run --project . python viewer/scripts/make_spectral_timeline.py
```

To watch it: serve the JSON as the viewer's timeline (the loader reads `/sample-timeline.json`) and open
the viewer — the transport bar scrubs/plays the frames; the universe grows node-by-node without spinning.

### When spectral helps (and when it won't)

- **Helps** when the corpus has a **connected component of ≥4 claims** linked by typed edges
  (entails / equivalence / evidence / defeat). That is where the eigenmap is meaningful and where the
  alignment kills the frame-to-frame thrash.
- **Won't look smoother** on tiny/disconnected corpora (every claim in its own ≤3-node group). There the
  eigenmap degenerates to a deterministic id-hash placement on a lattice, and the only motion is lattice
  re-indexing as components appear — which no global rotation can absorb. Use `--layout force` there.

### Guarantees

- **Deterministic** — same corpus sequence → byte-identical positions (sign-canonicalized eigenmap + SVD + 6dp).
- **`layout="force"` is byte-identical** to the pre-feature behavior.
- **Protocol untouched / numpy-free**; positions are injected through the existing
  `export_topology(positions=)` seam (`layout_id="external:spectral-v1"`).

---

## Part 2 — How it works (math & theory)

Give each claim a **meaningful 3-D position** — claims that are conceptually related (entailment,
equivalence, shared evidence) sit near each other; opposed claims repel — and make that map **evolve
smoothly** as the corpus grows live, instead of spinning/flipping every frame. Two ideas combine: a
signed-Laplacian **eigenmap** (the positions) and an orthogonal **Procrustes alignment** (the smoothness).

### 1. The signed-Laplacian eigenmap (`spectral_layout`)

**Graph.** From the resolved topology, build a weighted graph over claims. Each typed edge contributes an
attraction weight `w` (equivalence 1.0, entails 0.9, evidence_for 0.8, defeat-family 0.5, rebut 0.4);
strongest relation wins per pair. A `rebut` between **opposite-direction** conclusions is *polar* — its
weight is attenuated by ρ = 0.3, turning that pair into a net **repulsion**. This yields a signed symmetric
adjacency `A`.

**Embedding.** Per connected component (so unrelated subgraphs separate), form the **normalized signed
Laplacian**

```
L = I − D^(−1/2) · A · D^(−1/2),     D = diag(Σ_j |A_ij|)
```

and take the eigenvectors of the smallest eigenvalues, `L = Σ λ_k v_k v_kᵀ`. Skip the trivial null vector
(λ₁≈0, constant) and use the **next three** eigenvectors as the (x, y, z) coordinates. Intuition: this is the
relaxation of a min-cut / spring problem — minimizing `Σ_ij A_ij ‖x_i − x_j‖²` under a normalization
constraint pulls attractive pairs together and pushes repulsive (polar) pairs apart. Components needing <4
nodes fall back to a deterministic id-hash placement; components are tiled on a lattice and globally scaled.

### 2. Why a naïve live recompute thrashes

Eigenvectors are **not unique**. Each `v_k` is defined only up to **sign** (`−v_k` is an equally valid
eigenvector), and within any degenerate eigenspace (equal eigenvalues) up to an arbitrary **rotation**.
Formally the eigenbasis is fixed only modulo the orthogonal group O(k). A per-frame sign convention picks the
basis from the *current* frame's largest entry, so as the corpus changes by one claim, the whole embedding can
**flip or rotate** between frames. The viewer interpolates between frames, so this reads as the universe
*spinning* rather than *growing* — even though the underlying relational structure barely changed.

### 3. Orthogonal Procrustes alignment (`procrustes_align`)

Quotient out exactly that O(k) ambiguity by rigidly re-orienting each new frame onto the previous displayed
one. On the claims common to both frames, with `P` = previous positions and `Q` = new positions (each
centered, `P_c = P − P̄`, `Q_c = Q − Q̄`), solve the **orthogonal Procrustes problem**

```
R* = argmin_{RᵀR = I}  ‖ Q_c R − P_c ‖_F.
```

**Closed form (SVD).** Let `M = Q_cᵀ P_c` and `M = U Σ Vᵀ`. Then `R* = U Vᵀ`. *(Sketch: the objective expands
to a constant − 2·tr(RᵀM); over orthogonal R, tr(RᵀM) = tr(RᵀUΣVᵀ) is maximized when VᵀRᵀU = I, i.e. R = UVᵀ.)*
Apply this single transform to **every** new node — including newly-appeared claims, which thereby land in the
established frame instead of in raw eigenspace:

```
aligned[i] = (Q_i − Q̄) · R* + P̄.
```

**No determinant correction — deliberately.** The classic "rotation-only" Procrustes forces `det R = +1` by
flipping the last singular axis. We **don't**: a sign-flipped eigenvector *is* a reflection (`det = −1`), and
undoing it is the entire point. Allowing R over the full orthogonal group O(3) (rotations **and** reflections)
is what cancels the eigenbasis sign ambiguity. If fewer than **three** non-collinear common nodes exist (or no
previous frame), the 3-D rotation is underdetermined → the raw frame is returned as the reference (frame 0).

### 4. The chain, and what's left

Each frame aligns to the previous *displayed* frame (`NodeRunner._prev_spectral`), so consecutive frames
differ **only by the genuine corpus change** — a few nodes appearing or an edge re-weighting — never by a
basis flip. The viewer's existing inter-frame interpolation then renders smooth growth. Measured on a growing
≥4-node component: max per-node displacement drops from **≈2.70 (raw) to ≈1.27 (aligned)**, under half.

### 5. Scope and honest limits

Procrustes is a **rigid** map (rotation + reflection + translation): it removes basis ambiguity but cannot
absorb **non-rigid** churn. When a corpus has no ≥4-node component, `spectral_layout` degenerates to id-hash
balls tiled on a lattice whose index shifts as components appear — different points move in different
directions, which no single orthogonal R can fix (alignment can even worsen it). The mechanism therefore
applies precisely when the eigenmap is meaningful: a genuinely connected, growing relational graph.
Determinism is preserved throughout (sign-canonicalized eigenvectors + a deterministic SVD + 6-dp rounding).
