"""Build the viewer-loadable bundle for the UNIFIED Polymer Claims universe: a UNION of every
arm's already-decided claims (pharmaco/synbio/immuno/polymergenomics) into ONE faceted universe
— "one atom, many links" (`docs/superpowers/specs/2026-07-10-accumulating-universe-store-
design.md`). The atom is the content-addressed claim; which arm produced it and what modality it
reads are FACETS carried on each node (`arm`, `modality`), never a separate universe. Does NOT
re-run the licensing gate on the merge — every arm already decided its own claim statuses;
`merge_universes` (src/polymer_claims/merge_universes.py) only unions + dedups + tags them.

RUN (from the umbrella env so polymer_claims + polymer_protocol resolve; real GDSC pharmaco
data required, gitignored, ~1-2 min for the pharmaco arm's mechanism scan):
    cd /Users/zbb2/Desktop/polymer-claims \
      && uv run --project . python viewer/scripts/make_merged_universe.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from polymer_protocol import Layout, TimelineFrame, TopologyTimeline, export_topology, frame_stats

from polymer_claims.merge_universes import (
    ArmFacet,
    collect_immuno,
    collect_pharmaco,
    collect_polymergenomics,
    collect_synbio,
    collect_transposable_elements,
    collect_transposable_elements_enrichment,
    merge_universes,
)

_OUT = Path(__file__).resolve().parents[1] / "public" / "merged-universe.json"


def main(
    agent: Any | None = None,
    *,
    max_pairs: int = 500,
    threshold: float = 0.3,
) -> None:
    """Build the merged-universe bundle.

    Default (`agent is None`): the historical relation-free, FORCE_DIRECTED path — the
    output bundle is byte-identical to before this wiring existed.

    Optional relation pass (`agent` provided — an `LLMRelationAgent` or any object with a
    `.judge(claim_a, claim_b)` method): run `propose_relations` over the merged corpus,
    append the CONJECTURED relation claims BEFORE `export_topology`, and — because the
    corpus now carries cross-arm edges — inject `spectral_layout` positions through
    `export_topology`'s `positions=` seam (`layout_id="external:spectral-v1"`) instead of
    the id-hash force layout. When the agent proposes nothing, the force-directed default
    is kept (nothing changed).
    """
    print("collecting arms...", file=sys.stderr)

    synbio = collect_synbio()
    print(f"  synbio: {len(synbio.claims)} claims", file=sys.stderr)

    polymergenomics = collect_polymergenomics()
    print(f"  polymergenomics: {len(polymergenomics.claims)} claims", file=sys.stderr)

    immuno = collect_immuno()
    print(f"  immuno: {len(immuno.claims)} claims", file=sys.stderr)

    te_ndmp = collect_transposable_elements()
    print(f"  transposable-elements (n-DMP): {len(te_ndmp.claims)} claims", file=sys.stderr)

    te_enrichment = collect_transposable_elements_enrichment()
    print(f"  transposable-elements-enrichment: {len(te_enrichment.claims)} claims", file=sys.stderr)

    print("  pharmaco: running the real GDSC mechanism scan (~1-2 min)...", file=sys.stderr)
    pharmaco = collect_pharmaco()
    print(f"  pharmaco: {len(pharmaco.claims)} claims", file=sys.stderr)

    merged, facets = merge_universes(
        [pharmaco, synbio, immuno, polymergenomics, te_ndmp, te_enrichment])

    # Optional, agent-injected relation pass. When no agent is provided this whole block is
    # skipped and the bundle stays byte-identical to the relation-free force-directed output.
    use_spectral = False
    if agent is not None:
        from polymer_claims.relation_proposer import propose_relations

        relations = propose_relations(merged, agent, max_pairs=max_pairs, threshold=threshold)
        print(f"  relations proposed: {len(relations)}", file=sys.stderr)
        if relations:
            merged = merged.model_copy(update={"claims": merged.claims + tuple(relations)})
            for r in relations:
                facets[r.id] = ArmFacet(arm="relations", modality=None, topic=None)
            use_spectral = True  # cross-arm edges now exist -> spectral is meaningful

    n_by_arm = Counter(f.arm for f in facets.values())
    n_by_status = Counter(c.status.value for c in merged.claims)
    print(f"merged: {len(merged.claims)} total claims", file=sys.stderr)
    print(f"  by arm: {dict(sorted(n_by_arm.items()))}", file=sys.stderr)
    print(f"  by status: {dict(sorted(n_by_status.items()))}", file=sys.stderr)

    if use_spectral:
        # Inject the signed-Laplacian eigenmap through export_topology's positions= seam
        # (layout_id="external:spectral-v1"); see node.py::_spectral_positions.
        from polymer_claims.embedding import spectral_layout

        topo = export_topology(
            merged, layout=Layout.FORCE_DIRECTED, positions=spectral_layout(merged)
        )
    else:
        topo = export_topology(merged, layout=Layout.FORCE_DIRECTED)
    stats = frame_stats(merged, topo, cycle_index=0, n_frontier=0, n_added=0, n_newly_licensed=0)
    timeline = TopologyTimeline(frames=(TimelineFrame(topology=topo, stats=stats),), n_cycles=0)

    doc = timeline.model_dump(mode="json")
    # Tag arm + modality onto each node — the facet map merge_universes returns, surfaced the
    # only way it can be without touching the protocol's TopologyNode schema: extra keys on the
    # plain JSON dict, added AFTER model_dump (so the protocol/grammar contract stays untouched).
    n_untagged = 0
    for node in doc["frames"][0]["topology"]["nodes"]:
        facet = facets.get(node["id"])
        if facet is None:
            n_untagged += 1
            node["arm"] = None
            node["modality"] = None
            node["topic"] = None
        else:
            node["arm"] = facet.arm
            node["modality"] = facet.modality
            node["topic"] = facet.topic
    if n_untagged:
        raise SystemExit(f"{n_untagged} merged node(s) have no arm facet — every claim must be tagged")

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(doc, indent=2) + "\n")
    print(
        f"wrote {_OUT} ({len(topo.nodes)} nodes, {len(topo.edges)} edges, "
        f"layout={topo.layout_id})",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
