"""Append the two transposable-element arms to the EXISTING merged-universe.json in place.

The canonical rebuild (make_merged_universe.py) re-runs pharmaco's live GDSC mechanism scan, which needs
the `pharmaco` extra AND the raw GDSC data on disk — neither is present in every environment. This script
is the no-pharmaco path: it takes the already-built merged-universe.json (pharmaco/synbio/immuno/
polymergenomics baked in) and folds in the TE n-DMP + TE enrichment arms, which load cleanly from their
committed strict-Corpus bundles. The existing arms' force-directed layout CANNOT be recomputed without the
pharmaco corpus, so the TE nodes are laid out on their own and TRANSLATED to a distinct island beside the
main cloud (honest: an appended region, not a co-optimized layout). Idempotent — re-running replaces the
TE island rather than duplicating it.

RUN (from the umbrella env):
    cd /Users/zbb2/Desktop/polymer-claims \
      && uv run --project . python viewer/scripts/add_te_arms_to_merged.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from polymer_protocol import Layout, export_topology

from polymer_claims.merge_universes import (
    collect_transposable_elements,
    collect_transposable_elements_enrichment,
    merge_universes,
)

_MERGED = Path(__file__).resolve().parents[1] / "public" / "merged-universe.json"
_TE_ARMS = ("transposable-elements", "transposable-elements-enrichment")
_ISLAND_OFFSET = (9.0, 0.0, 0.0)     # translate the TE cloud clear of the existing [-3,3] universe


def _te_nodes_and_edges() -> tuple[list[dict], list[dict]]:
    """Build the two TE arms, lay them out, and return arm-tagged node + edge dicts (island-offset)."""
    merged, facets = merge_universes([
        collect_transposable_elements(),
        collect_transposable_elements_enrichment(),
    ])
    topo = export_topology(merged, layout=Layout.FORCE_DIRECTED)
    dumped = topo.model_dump(mode="json")
    nodes = dumped["nodes"]
    for n in nodes:
        f = facets.get(n["id"])
        n["arm"] = f.arm if f else None
        n["modality"] = f.modality if f else None
        n["topic"] = f.topic if f else None
        pos = n.get("position")
        if isinstance(pos, list) and len(pos) == 3:
            n["position"] = [pos[i] + _ISLAND_OFFSET[i] for i in range(3)]
    return nodes, dumped.get("edges", [])


def main() -> None:
    if not _MERGED.exists():
        raise SystemExit(f"{_MERGED} not found — build it first (make_merged_universe.py)")
    doc = json.loads(_MERGED.read_text())
    topo = doc["frames"][0]["topology"]

    # Idempotent: drop any prior TE island (by arm tag) + edges touching those ids.
    prior_te_ids = {n["id"] for n in topo["nodes"] if n.get("arm") in _TE_ARMS}
    topo["nodes"] = [n for n in topo["nodes"] if n.get("arm") not in _TE_ARMS]
    topo["edges"] = [e for e in topo["edges"]
                     if e.get("source") not in prior_te_ids and e.get("target") not in prior_te_ids]

    te_nodes, te_edges = _te_nodes_and_edges()
    existing_ids = {n["id"] for n in topo["nodes"]}
    te_nodes = [n for n in te_nodes if n["id"] not in existing_ids]  # never shadow an existing atom

    topo["nodes"].extend(te_nodes)
    topo["edges"].extend(te_edges)

    by_arm = Counter(n.get("arm") for n in topo["nodes"])
    by_te_status = Counter(n.get("status") for n in te_nodes)
    print(f"added {len(te_nodes)} TE nodes ({dict(by_te_status)}), {len(te_edges)} TE edges",
          file=sys.stderr)
    print(f"merged-universe now: {len(topo['nodes'])} nodes; by arm: {dict(sorted(by_arm.items()))}",
          file=sys.stderr)

    _MERGED.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {_MERGED}", file=sys.stderr)


if __name__ == "__main__":
    main()
