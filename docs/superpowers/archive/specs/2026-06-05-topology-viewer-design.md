# 3D claim-topology viewer — design spec (data contract + decomposition)

> **Status:** design / decomposition spec, 2026-06-05 (autonomous-overnight; produced at the user's request
> to "set up a plan for designing the 3D viewer"). **Decomposition + data contract only — do NOT build the
> viewer here.** The live viewer + compute layer are being built in a SEPARATE instance
> ([[project_polymer_claims_platform_vision]]); this repo's contribution is the **export contract** the
> viewer consumes. Scale-gated: only interesting at thousands+ of claims (the scaling-law regime).

## Goal

A navigable **3D latent-space view of the claims universe**: clusters and chains laid out in space,
fly-through navigation, click-a-claim to inspect, lasso-a-cluster to subset — so the **network topology
itself becomes a subject** of study (the deferred capstone from the unified spec). It extends the existing
`PolymerGenomicsAPI/viewer` FormalClaimUniverse + `/portal/latent3d` surface (a different repo).

## Division of labor (important)

- **This repo (`polymer-claims`)** owns the **data contract**: a pure, deterministic export of the corpus
  as a topology graph the viewer can render. This is the only piece that should ever live here.
- **The separate viewer instance** owns rendering, camera, interaction, WebGL/Three.js, the portal route —
  all of it. Do not duplicate that here.

So the buildable-here artifact is a `topology export` (corpus → a JSON graph with positions + attributes),
NOT a renderer.

## The data contract — `TopologyExport`

A pure function in `polymer_protocol` (a future small slice, when scale warrants):
`export_topology(corpus, *, layout) -> TopologyExport`. Shape (all frozen, JSON-serializable):

```
TopologyNode:
    id: str
    status: str                       # conjectured/exploratory/pending/licensed/rejected
    pattern_id: str                   # for clustering/coloring
    subject_kind: str | None          # genomic_region/variant_vrs/.../None — clustering axis
    strength: tuple[float, ...] | None # the 6-axis vector (for size/color encodings)
    is_representation_revision: bool   # meta-tier claims render distinctly
    position: tuple[float, float, float]  # 3D coordinates from the layout

TopologyEdge:
    source: str
    target: str
    kind: str                         # defeat-kind (undermine/undercut/rebut/...) | "equivalence" | "entails"
    effective: bool                   # is this edge currently effective (post grounded-extension)?
    provisional: bool                 # activate-on-license edges render dashed/ghosted

TopologyCluster:                      # optional pre-computed grouping for lasso/coloring
    id: str
    label: str                        # e.g. "pattern:adjusted_effect" or "subject:genomic_region"
    member_ids: tuple[str, ...]

TopologyExport:
    nodes: tuple[TopologyNode, ...]
    edges: tuple[TopologyEdge, ...]
    clusters: tuple[TopologyCluster, ...]
    layout_id: str                    # which layout produced the positions (for reproducibility)
```

The viewer renders nodes at `position`, colors/sizes by `status`/`strength`/`pattern_id`, draws edges by
`kind`/`effective`/`provisional`, and uses `clusters` for lasso/legend. Everything the viewer needs is in
the export; the viewer never re-derives epistemic state.

## Layout (the one real algorithmic choice)

Positions come from a **deterministic** layout over the claim graph (the runtime is pure/deterministic — no
clock/random, so the layout must seed deterministically). Options:
- **Force-directed (Fruchterman-Reingold/ForceAtlas) over the defeat ∪ entails graph**, seeded
  deterministically — clusters emerge from connectivity. Most faithful to "topology as subject."
- **Embedding-derived** (if/when claims gain vector embeddings) projected to 3D via a deterministic PCA/UMAP
  with a fixed seed — clusters emerge from semantic similarity. Needs the embedding substrate (not built).
- **Attribute grid** (pattern × subject_kind × status lattice) — trivial, deterministic, but not
  "topological."

Recommend: ship the **force-directed** layout first (operates on the existing graph, no new substrate),
with `layout_id` recording the algorithm+seed for reproducibility. The embedding layout is a later upgrade
when the embedding operators land (the #4b-3 seam's real injected adapters).

## Interactions (viewer-side — listed for the contract, not built here)

- **Fly-through** — free camera over the point cloud.
- **Click-claim** — select a node → the viewer fetches/inspects that claim's full record (the export's
  `id` keys back into the corpus / an API).
- **Lasso-cluster** — select a spatial region → subset by `member_ids` / spatial bounds.
- **Filter** — by status / pattern / subject_kind / effective-vs-provisional edges (all in the export).
- **Time-scrub** (stretch) — replay the corpus across `run_cycle` iterations (needs a sequence of exports).

## Scale-gating (why this is deferred)

The view is only meaningful at **thousands+ of claims** — the scaling-law regime where the topology has
structure worth navigating. At the current corpus size (tests + small fixtures) a 3D view shows a handful
of points. So: build the export contract when a real corpus approaches that scale; until then this spec is
the plan, not a task.

## Decomposition (when scale + the separate viewer are ready)

1. **`export_topology` (here, small protocol slice)** — the pure corpus→`TopologyExport` function + the
   force-directed deterministic layout + JSON serialization + tests. This is the ONLY part that lands in
   `polymer-claims`.
2. **Viewer ingestion (separate instance)** — the `/portal/latent3d` route consumes `TopologyExport`;
   render nodes/edges/clusters; camera + click + lasso. Owned by the viewer repo.
3. **Live updates (separate instance)** — stream successive exports as the corpus evolves (the "watch the
   claims universe live" platform-vision goal).

## Out of scope

- Any rendering/WebGL/route code (separate instance owns it).
- The embedding-derived layout (needs the embedding substrate from real #4b-3 adapters).
- Building `export_topology` now (scale-gated — write it when a corpus approaches thousands of claims).
