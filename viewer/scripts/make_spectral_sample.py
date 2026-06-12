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
