# Relational Graph Embedding (v1) — design

**Status:** Design / phase spec. v0.1
**Date:** 2026-06-12
**Author:** Z. Belden

## 0. Goal & hypothesis

Replace the viewer's placeholder node positions — today a Fruchterman–Reingold layout seeded from
SHA-256 of the claim id (`protocol/topology.py`), which encodes graph *adjacency plus noise*, not
conceptual content — with a **meaningful relational embedding**: a map from each claim to a point in
3D where **distance approximates conceptual dissimilarity**. Claims about the same question (linked
by entailment / equivalence / shared neighborhood) cluster; unrelated claims separate; claims that
*disagree* on the same question sit **near but not coincident**.

**The hypothesis this slice tests:** the corpus's asserted relational edges (the proposition
neighborhood + the defeat graph + equivalences) already carry most of the conceptual structure — so
a faithful embedding of *those edges alone*, with no semantic/content features and no learned model,
produces a space whose clusters are meaningful. If clusters come out under-connected, that failure is
the evidence that content features are needed (a later slice). This is the cleanest, most
interpretable test of that hypothesis: every node's position is explainable from its edges.

Out of scope for v1 (deferred, see §8): live-streaming stability, UMAP projection, content/semantic
features.

## 1. Architecture & boundaries

The eigensolve needs `numpy` (linear algebra), which is impure relative to the pure-`math` protocol
core. The split:

- **Umbrella module `src/polymer_claims/embedding.py`** (impure; `numpy`): the embedding itself —
  `spectral_layout(corpus) -> dict[str, tuple[float, float, float]]`. Builds the typed-weighted
  graph from a `Corpus`, computes the signed-Laplacian eigenmap, returns deterministic 3D positions
  keyed by claim id. This is where all numerical work lives.
- **One additive protocol change** — `export_topology(corpus, *, layout, seed_positions=None,
  positions=None)`: a new optional `positions: dict[str, tuple[float,float,float]] | None`. When
  supplied, `export_topology` uses those positions verbatim (skipping FR) and sets
  `layout_id="external:spectral-v1"`; when omitted, behavior is **byte-identical** to today. Protocol
  gains **no numpy** — it only accepts a dict and reuses its existing pure node/edge/cluster
  assembly. Corpus stays 4 collections; grammar untouched; one-way isolation intact.
- **Experiment harness `viewer/scripts/make_spectral_sample.py`** (umbrella env): builds a synthetic
  corpus, calls `spectral_layout`, then `export_topology(corpus, layout=FORCE_DIRECTED,
  positions=<spectral>)`, writes `viewer/public/sample-topology-spectral.json`. The viewer already
  renders `position` positionally, so **no viewer code change** is needed to look at the result.

Boundary rationale: the *embedding* (numbers) is impure and umbrella-side; the *assembly* of a
`TopologyExport` from positions is pure and stays in protocol; the optional param is the single
narrow seam between them.

## 2. The typed-weighted graph

Nodes = **claim ids only** (synthetic `:`-prefixed defeat-source nodes that appear in the topology
are omitted from the embedding for v1). One symmetric weighted adjacency `W` over claim ids.

**Edge source — reuse the resolved topology edges.** v1 sources its graph from
`export_topology(corpus, layout=NONE).edges` — the same id→id edge set the viewer already draws as
lines (so the embedding is consistent with the rendered graph, and protocol's neighborhood/defeat
resolution is reused rather than re-implemented). That set is `entails ∪ equivalence ∪ defeat-kinds`.
Proposition-level `INCOMPATIBLE_WITH` is **not** in that export today (only `ENTAILS` neighborhood is
resolved), so it is **deferred to v1.1** (when/if it is added to the topology edge export); the
polarity behavior it would serve is fully covered by `REBUT` for v1 (see below).

**Every conceptual edge is attractive**, weighted by kind (the weight is a stated conceptual
commitment, tunable, defaults below):

| Edge kind (as exported) | Weight `w` | Meaning |
|---|---|---|
| `equivalence` (LICENSED / STRUCTURAL) | 1.0 | same claim → near-coincident |
| `entails` | 0.9 | implies → very close |
| `evidence_for` | 0.8 | supports → close |
| `undermine`, `undercut`, `reclassify`, `reinterpret` | 0.5 | attacks premise/warrant/framing — related but oblique |
| `rebut` | 0.4 | same question, contrary conclusion |
| *(`incompatible_with` — deferred v1.1)* | *0.4* | *same question, mutually exclusive* |

Edges are symmetrized (`W[i,j] = W[j,i] = max` of any contributing kinds; multiple edges between a
pair take the max, not the sum, so a single strong relation isn't diluted by weak ones).

**Polarity term (the "near but not coincident" requirement).** For a `rebut` pair whose two claims'
Propositions (their `conclusion`) have **opposite `direction`** (POSITIVE vs NEGATIVE), add a signed
**repulsion** `-ρ` (default `ρ = 0.3`) to a separate signed matrix `R[i,j]`. The shared neighborhood
still attracts them (common neighbors → pulled close); the repulsion nudges them apart along their
disagreement axis → near but separated. `NULL`-direction, same-direction, or missing-conclusion
pairs get no repulsion (merely related, not polar-opposed). (`incompatible_with` joins this rule in
v1.1.)

## 3. The embedding math

Signed normalized-Laplacian eigenmap, computed **per connected component** (this avoids the
disconnected-graph ambiguity where the null eigenvalue has multiplicity = #components, and it gives
the desired behavior that unrelated subgraphs separate). Deterministic throughout:

1. Split the graph into connected components (over the positive adjacency `W`; the polarity term `R̄`
   never connects otherwise-unconnected nodes, so it doesn't affect components).
2. **For each component with ≥ 4 nodes:** form the combined signed weight `A = W − ρ·R̄` restricted
   to the component (`W` all-positive attraction; `R̄` subtracts on the component's opposite-direction
   polar pairs only). Signed degree `D̄_ii = Σ_j |A_ij|`; signed normalized Laplacian
   `L = I − D̄^{-1/2} A D̄^{-1/2}` (Kunegis form — symmetric). Eigendecompose via `numpy.linalg.eigh`
   (deterministic for symmetric matrices); take the eigenvectors for the **3 smallest eigenvalues
   above the single trivial null** → the component's local (x, y, z).
3. **For each component with < 4 nodes** (too few for a 3-D eigenmap): deterministic id-hash fallback
   positions within a small local ball.
4. **Place the components** in a shared frame on a coarse deterministic lattice (ordered by each
   component's sorted minimum claim-id), each component's local coords scaled into its lattice cell —
   so components don't overlap at the origin and larger/denser ones get proportional room.
5. **Sign canonicalization** (determinism across BLAS/platforms, where `eigh`'s sign is arbitrary):
   flip each eigenvector so its largest-|magnitude| component is positive; ties broken by lowest
   index. Final coordinates scaled to `[-1, 1]` overall and rounded to 6 dp → byte-stable output.

**Degenerate cases (covered by the per-component method above):**
- **Isolated nodes** (single-node components): the < 4-node fallback (step 3) places them by id-hash
  in their own lattice cells, well away from cluster mass. The harness logs "N isolated nodes (no
  relational signal)."
- **Empty / very small corpus:** falls entirely into steps 3–4; `spectral_layout` never raises on
  small input and never returns NaN.

## 4. The protocol seam

`export_topology` gains `positions: dict[str, tuple[float,float,float]] | None = None`:

- `positions is None` → today's behavior exactly (FR or NONE per `layout`), output byte-identical.
- `positions` supplied → each node's `position` is taken from the dict (missing id → `(0,0,0)` with
  a one-line note in `layout_id`), `layout_id = "external:spectral-v1"`, FR is **not** run. `layout`
  is ignored when `positions` is supplied (documented).

This is purely additive, numpy-free, and reuses the existing assembly path. The `CONTRACT_VERSION`
on `TopologyExport` does **not** change (the node/edge schema is unchanged; only the position
*source* differs, which `layout_id` already records).

## 5. The experiment harness & synthetic corpus

`viewer/scripts/make_spectral_sample.py` (sibling of `make_sample.py`; run from the umbrella env so
both `polymer_claims` + numpy and `polymer_protocol` resolve:
`uv run --project . python viewer/scripts/make_spectral_sample.py`).

It builds a **seeded synthetic corpus with K = 3 planted conceptual clusters** (deterministic, no
RNG — structure by construction):
- Each cluster: ~8 claims on a shared subject/estimand, densely linked by `ENTAILS` / `EVIDENCE_FOR`
  / a couple of `equivalence` edges (a tight conceptual neighborhood).
- Cross-cluster: sparse — only 1–2 links total, so clusters are genuinely separable.
- **Polarity probes:** within ≥1 cluster, a planted `REBUT` pair with opposite `direction` (the
  "opposite effect of the same gene" case) to exercise near-but-separated.
- A few isolated claims (no edges) to exercise the fallback.

It writes `viewer/public/sample-topology-spectral.json`. You load it in the viewer (sample mode) and
look. (Whether to add a viewer toggle between the FR sample and the spectral sample is a trivial
later nicety, not part of v1 — for now it is a second sample file.)

## 6. Success criteria & tests

"Meaningful" is made **testable**, not just eyeballed. Tests live umbrella-side
(`tests/test_embedding.py`), operating on the synthetic corpus the harness uses (factored into a
shared builder so the test and the harness embed the same graph):

1. **Cluster separation (the core hypothesis):** compute mean pairwise distance within each planted
   cluster vs. between clusters; assert **mean-intra < mean-inter** by a margin (a silhouette-style
   score `> 0.25`). This is the objective evidence that the edges carry the structure.
2. **Polarity (near-but-separated):** the planted opposite-`direction` `REBUT` pair has distance
   **> 0** (not coincident) and **< the inter-cluster mean** (still near). 
3. **Equivalence (near-coincident):** an `equivalence`-linked pair is the closest pair in its
   cluster.
4. **Determinism:** `spectral_layout(corpus)` called twice → byte-identical dict; sign
   canonicalization holds (a test that perturbs eigenvector signs and confirms the canonical output
   is stable).
5. **Degenerate handling:** isolated node gets a finite, non-NaN position off the cluster mass;
   empty / 2-node corpus returns without raising.
6. **Protocol back-compat:** `export_topology(corpus, layout=FORCE_DIRECTED)` (no `positions`) is
   byte-identical to before this change (assert against a committed fixture); `positions=` override
   sets `layout_id="external:spectral-v1"` and uses the supplied coordinates.
7. **`check-all.sh` ALL GREEN** — grammar / protocol / umbrella / isolation / viewer build unaffected.

The visual look in the viewer is the human-judgment complement to (1)–(3), not a substitute.

## 7. Dependencies

`numpy` is added to the **umbrella** package only (`pyproject.toml` of `polymer-claims`). Protocol
and grammar gain no new dependency (the protocol seam accepts a plain dict). If a leaner footprint is
wanted later, the eigensolve is small enough to hand-roll, but numpy is the pragmatic v1 choice and
is already anticipated in the codebase (`exec_adapters.py` names numpy as a future swap-in).

## 8. Scope fences & deferred

- **Live-streaming stability (Approach C)** — recomputing the eigenmap each frame would make nodes
  jump; the live `NodeRunner`/SSE path keeps using FR's warm-start for now. Porting the embedding
  into the live viewer (spectral positions + warm-start interpolation between recomputes) is the next
  slice. v1 is a **static snapshot** only.
- **UMAP (Approach B)** — spectral straight to 3D for v1. Embedding to N-dim → UMAP-to-3D for crisper
  clusters (and the literal pipeline) is a later refinement; it brings the `umap-learn` dep and
  UMAP's global-distance distortion, neither worth it until clusters are dense.
- **Content / semantic features** — relational edges only. If §6.1 separation is weak, that is the
  signal to add content features (a later slice); v1's job is to find out.
- **Viewer UX** — no in-viewer toggle / lasso / cluster labels in v1 (a second sample file is enough
  to look). Tracked for later.

## 9. Invariants preserved

- **Grammar untouched; Corpus stays 4 collections;** protocol gains one additive optional param and
  **no numpy**.
- **Determinism preserved** despite numpy: deterministic `eigh` + sign canonicalization + rounding →
  byte-stable, in keeping with the project's no-clock/no-random character.
- **Interpretability** — every position is explainable from typed edges with stated weights; no
  learned model, no hidden scalar.
- **Back-compat** — `export_topology` without `positions` is byte-identical; the viewer contract
  version is unchanged.
