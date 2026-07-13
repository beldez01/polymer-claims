"""Fold the transposable-element arms into the EXISTING merged-universe.json in place (no pharmaco rerun).

The canonical rebuild (make_merged_universe.py) re-runs pharmaco's live GDSC scan, which needs the
`pharmaco` extra AND raw GDSC data on disk — absent in many environments. This is the no-pharmaco path: it
takes the already-built merged-universe.json (pharmaco/synbio/immuno/polymergenomics baked in) and folds in
the TE arms, each of which loads cleanly from a committed strict-Corpus bundle. The existing arms'
force-directed layout CANNOT be recomputed without the pharmaco corpus, so each TE bundle is laid out on
its OWN and translated to a distinct island beside the main cloud (honest: appended regions, not a
co-optimized layout). Idempotent — re-running replaces the TE islands rather than duplicating them.

Islands folded in (curated headline arms + the full multi-contrast campaign):
  * transposable-elements                (6 n-DMP families, lymphoid-vs-myeloid, LICENSED)
  * transposable-elements-enrichment     (6 enrichment families, 0 licensed — the honest recast)
  * te-campaign-ndmp                      (72 n-DMP claims across 12 contrasts)
  * te-campaign-enrichment               (72 enrichment claims across 12 contrasts, 0 licensed)

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

from polymer_claims.io import load_corpus

_VIEWER = Path(__file__).resolve().parents[1]
_MERGED = _VIEWER / "public" / "merged-universe.json"
_DEMO = _VIEWER.parents[0] / "data" / "demo"

# (arm label, bundle path, island translation). Offsets park each island clear of the [-3.5, 3.5] main
# cloud AND of each other; the campaign islands (72 nodes) get wider separation than the 6-node headliners.
_ISLANDS: tuple[tuple[str, Path, tuple[float, float, float]], ...] = (
    ("transposable-elements", _DEMO / "transposable_elements_universe.json", (9.0, 3.5, 0.0)),
    ("transposable-elements-enrichment", _DEMO / "transposable_elements_enrichment_universe.json",
     (9.0, -3.5, 0.0)),
    ("te-campaign-ndmp", _DEMO / "campaign" / "te_campaign_ndmp_universe.json", (17.0, 9.0, 0.0)),
    ("te-campaign-enrichment", _DEMO / "campaign" / "te_campaign_enrichment_universe.json",
     (17.0, -9.0, 0.0)),
)
_TE_ARM_LABELS = frozenset(a for a, _, _ in _ISLANDS)


def _island_nodes(arm: str, bundle: Path, offset) -> list[dict]:
    """Lay out one bundle on its own and return arm-tagged, island-offset node dicts."""
    corpus = load_corpus(str(bundle))
    topo = export_topology(corpus, layout=Layout.FORCE_DIRECTED)
    nodes = topo.model_dump(mode="json")["nodes"]
    for n in nodes:
        n["arm"] = arm
        n["modality"] = "methylation"
        n["topic"] = None
        pos = n.get("position")
        if isinstance(pos, list) and len(pos) == 3:
            n["position"] = [pos[i] + offset[i] for i in range(3)]
    return nodes


def main() -> None:
    if not _MERGED.exists():
        raise SystemExit(f"{_MERGED} not found — build it first (make_merged_universe.py)")
    doc = json.loads(_MERGED.read_text())
    topo = doc["frames"][0]["topology"]

    # Idempotent: drop any prior TE islands (by arm label) + edges touching them.
    prior = {n["id"] for n in topo["nodes"] if n.get("arm") in _TE_ARM_LABELS}
    topo["nodes"] = [n for n in topo["nodes"] if n.get("arm") not in _TE_ARM_LABELS]
    topo["edges"] = [e for e in topo["edges"]
                     if e.get("source") not in prior and e.get("target") not in prior]

    existing_ids = {n["id"] for n in topo["nodes"]}
    added = 0
    for arm, bundle, offset in _ISLANDS:
        if not bundle.exists():
            print(f"  (skip missing bundle {bundle.name})", file=sys.stderr)
            continue
        nodes = [n for n in _island_nodes(arm, bundle, offset) if n["id"] not in existing_ids]
        existing_ids.update(n["id"] for n in nodes)
        topo["nodes"].extend(nodes)
        st = Counter(n.get("status") for n in nodes)
        print(f"  +{len(nodes):>3} {arm:<34} {dict(st)}", file=sys.stderr)
        added += len(nodes)

    by_arm = Counter(n.get("arm") for n in topo["nodes"])
    print(f"added {added} TE nodes total", file=sys.stderr)
    print(f"merged-universe now: {len(topo['nodes'])} nodes; by arm: {dict(sorted(by_arm.items()))}",
          file=sys.stderr)

    # Recompute the frame stats from the FINAL node/edge set. The base bundle's stats were computed by
    # make_merged_universe before these islands were folded in; without this the HUD under-reports
    # (e.g. n_nodes/n_licensed frozen at the pre-fold values). Mirrors polymer_protocol.frame_stats.
    stats = doc["frames"][0].setdefault("stats", {})
    st = Counter(n.get("status") for n in topo["nodes"])
    stats.update(
        n_nodes=len(topo["nodes"]),
        n_licensed=st.get("licensed", 0),
        n_pending=st.get("pending", 0),
        n_conjectured=st.get("conjectured", 0),
        n_rejected=st.get("rejected", 0),
        n_edges=len(topo["edges"]),
        n_effective_edges=sum(1 for e in topo["edges"] if e.get("effective")),
        n_provisional_edges=sum(1 for e in topo["edges"] if e.get("provisional")),
    )
    print(f"recomputed stats: {dict(st)}", file=sys.stderr)

    _MERGED.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {_MERGED}", file=sys.stderr)


if __name__ == "__main__":
    main()
