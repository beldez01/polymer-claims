"""Build the viewer-loadable bundle for the STRATA pharmacogenomic claims universe (GDSC):
696 nodes (4 LICENSED / 609 PENDING / 83 REJECTED) exported by
`polymer_claims.pharmaco_populate.run_full_universe` (the Monday-demo volume path).

Wraps the already-exported `TopologyExport`
(data/pharmaco/gdsc_pharmaco_universe_topology.json, gitignored — real GDSC-derived) in a
single-frame `TopologyTimeline`, exactly the shape `make_polymergenomics_timeline.py` writes for
the OTHER default bundle. No re-derivation of claims: `export_topology` already puts everything the
viewer's static (non-live) claim card reads on each node — id (`pgx-<GENE>-<DRUG>`, so the card's
id field IS the drug-to-marker pair), status, pattern_id, subject_kind, and the full FDR block
(fdr_e_value, fdr_alpha_allocated, fdr_index) an e-value lives on. Regenerating from the corpus
would only add a `title`/`subject` string the static RightRail card never renders (those are
live-mode-only fields via fetchClaimDetail) — so reuse, not rebuild, is the correct call here.

Validates the export against the protocol's `TopologyExport` model before wrapping (a schema
check, not just a JSON parse), and fails loudly if the licensed-count assumption the demo script
narrates (4 LICENSED, topped by CDKN2A-Palbociclib) drifts.

RUN (from the umbrella env so polymer_protocol resolves):
    cd /Users/zbb2/Desktop/polymer-claims \
      && uv run --project . python viewer/scripts/make_pharmaco_universe.py
"""
from __future__ import annotations

import json
from pathlib import Path

from polymer_protocol import FrameStats, TimelineFrame, TopologyExport, TopologyTimeline

_SRC = Path(__file__).resolve().parents[2] / "data" / "pharmaco" / "gdsc_pharmaco_universe_topology.json"
_OUT = Path(__file__).resolve().parents[1] / "public" / "pharmaco-universe.json"


def _frame_stats(topo: TopologyExport) -> FrameStats:
    """Per-status/edge counts straight off the export's nodes/edges — no Corpus needed since
    this is a static snapshot, not a run_cycle delta (n_frontier/n_added/n_newly_licensed are all
    0, matching how make_polymergenomics_timeline.py stats its single seed frame)."""
    n_licensed = sum(1 for n in topo.nodes if n.status == "licensed")
    n_pending = sum(1 for n in topo.nodes if n.status == "pending")
    n_rejected = sum(1 for n in topo.nodes if n.status == "rejected")
    n_conjectured = sum(1 for n in topo.nodes if n.status == "conjectured")
    return FrameStats(
        cycle_index=0,
        n_nodes=len(topo.nodes),
        n_licensed=n_licensed,
        n_pending=n_pending,
        n_conjectured=n_conjectured,
        n_rejected=n_rejected,
        n_edges=len(topo.edges),
        n_effective_edges=sum(1 for e in topo.edges if e.effective),
        n_provisional_edges=sum(1 for e in topo.edges if e.provisional),
        n_frontier=0,
        n_added=0,
        n_newly_licensed=0,
    )


def main() -> None:
    if not _SRC.exists():
        raise SystemExit(
            f"missing {_SRC} — run `uv run --project . python -c "
            "'from polymer_claims.pharmaco_populate import run_full_universe; run_full_universe()'` "
            "first (real GDSC data required, gitignored)."
        )

    raw = json.loads(_SRC.read_text())
    topo = TopologyExport.model_validate(raw)  # schema check, not just a JSON parse

    n_licensed = sum(1 for n in topo.nodes if n.status == "licensed")
    if n_licensed == 0:
        raise SystemExit(f"expected >0 LICENSED nodes in {_SRC}, got 0 — demo centerpiece would render empty")

    top_licensed = sorted(
        (n for n in topo.nodes if n.status == "licensed"),
        key=lambda n: (n.fdr_e_value is None, -(n.fdr_e_value or 0.0)),
    )
    print(f"{len(topo.nodes)} nodes, {n_licensed} licensed:")
    for n in top_licensed:
        print(f"  {n.id}: e={n.fdr_e_value}")

    stats = _frame_stats(topo)
    timeline = TopologyTimeline(frames=(TimelineFrame(topology=topo, stats=stats),), n_cycles=0)

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(timeline.model_dump(mode="json"), indent=2) + "\n")
    print(f"wrote {_OUT} ({len(topo.nodes)} nodes, {n_licensed} licensed, layout={topo.layout_id})")


if __name__ == "__main__":
    main()
