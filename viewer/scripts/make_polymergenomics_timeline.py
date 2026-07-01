"""Build the viewer's DEFAULT bundled timeline from the PolymerGenomics reference seed.

Replaces the old 14-node toy demo (viewer/public/sample-timeline.json) with a single-frame
TopologyTimeline of the real 47-claim universe, laid out by the signed-Laplacian eigenmap. Uses
ONLY pure functions (export_topology + spectral_layout) — no run_cycle, so NO synthetic claims are
generated; it is exactly the seed corpus, positioned.

RUN (from the umbrella env so polymer_claims + numpy + polymer_protocol resolve):
    cd /Users/zbb2/Desktop/polymer-claims \
      && uv run --project . python viewer/scripts/make_polymergenomics_timeline.py
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
)

from polymer_claims.embedding import spectral_layout
from polymer_claims.io import load_corpus

_SEED = Path(__file__).resolve().parents[2] / "data" / "demo" / "polymergenomics_universe.json"
_OUT = Path(__file__).resolve().parents[1] / "public" / "sample-timeline.json"


def main() -> None:
    corpus = load_corpus(str(_SEED))
    positions = spectral_layout(corpus)
    topo = export_topology(corpus, layout=Layout.FORCE_DIRECTED, positions=positions)
    stats = frame_stats(
        corpus, topo, cycle_index=0, n_frontier=0, n_added=0, n_newly_licensed=0,
    )
    timeline = TopologyTimeline(frames=(TimelineFrame(topology=topo, stats=stats),), n_cycles=0)
    _OUT.write_text(json.dumps(timeline.model_dump(mode="json"), indent=2) + "\n")
    last = timeline.frames[-1].topology
    print(f"wrote {_OUT} ({len(timeline.frames)} frame, {len(last.nodes)} nodes, "
          f"layout={last.layout_id})")


if __name__ == "__main__":
    main()
