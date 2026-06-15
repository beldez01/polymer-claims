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
    licensed_prev = 0
    for i, corpus in enumerate(corpora):
        aligned = procrustes_align(prev_spectral, spectral_layout(corpus))
        prev_spectral = aligned
        topo = export_topology(corpus, layout=Layout.FORCE_DIRECTED, positions=aligned)
        licensed_now = n_licensed(corpus)
        stats = frame_stats(
            corpus,
            topo,
            cycle_index=i,
            n_frontier=0,
            n_added=0,
            n_newly_licensed=max(0, licensed_now - licensed_prev),
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
