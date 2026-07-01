"""Build the viewer's default bundle: the 47-claim PolymerGenomics universe PLUS one genuinely
LICENSED n-DMP claim, so the viewer shows the first earned (blue) node beside the witnessed imports
and the sheaf gauge gains its first real vertex.

The licensed node uses the SYNTHETIC n-DMP (se:tcga_laml_idh_synth@1) — same real gate, deterministic
and reproducible (the real-data proof, LICENSED @ REPRODUCED on TCGA-LAML, is the biology validation
via `verify-kernel --real`; its 663 MB inputs are gitignored, so the committed bundle uses the
synthetic run, which is byte-reproducible here). Pure functions for layout — no run_cycle beyond the
one gate run that mints the license.

RUN (umbrella env):
    cd /Users/zbb2/Desktop/polymer-claims \
      && uv run --project . python viewer/scripts/make_universe_timeline.py
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from polymer_protocol import (
    Corpus,
    Layout,
    TimelineFrame,
    TopologyTimeline,
    export_topology,
    frame_stats,
    run_cycle,
)

from polymer_claims._ndmp_gate import run_ndmp_gate
from polymer_claims.contracts import clear_contract_cache, using_contract_root
from polymer_claims.embedding import spectral_layout
from polymer_claims.ingest.synthetic import build_synthetic_contract
from polymer_claims.io import load_corpus

_SEED = Path(__file__).resolve().parents[2] / "data" / "demo" / "polymergenomics_universe.json"
_OUT = Path(__file__).resolve().parents[1] / "public" / "sample-timeline.json"


def _licensed_ndmp_claim():
    """Drive the synthetic n-DMP claim through the real gate and return the LICENSED Claim object."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build_synthetic_contract(root)
        with using_contract_root(root):
            clear_contract_cache()
            g = run_ndmp_gate("se:tcga_laml_idh_synth@1", "kernel-ndmp-licensed", alpha=0.05)
        clear_contract_cache()
    if g["status"] != "licensed":
        raise SystemExit(f"n-DMP claim did not license: status={g['status']!r}")
    return g["licensed_claim"]


def _licensed_hla_claim():
    """Phase 2: license the migrated HLA claim on real BLUEPRINT WGBS (datasets/hla_a_promoter_meth.csv)
    via the mean_diff air-gap, and return the LICENSED Claim (same id as the imported one, so it
    replaces the conjectured node in place)."""
    from polymer_grammar import FDRLedger, MaterializationContext

    from polymer_claims.exec_adapters import (
        StatsPureAdapter,
        StatsStdlibAdapter,
        apparatus_oracle_registry,
        hla_promoter_meth_claim,
        independent_registry,
    )

    ctx = MaterializationContext(id="M1", api_version="v1", data_version="blueprint_wgbs@2016")
    c = hla_promoter_meth_claim()
    result = run_cycle(
        Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05)),
        (StatsPureAdapter(), StatsStdlibAdapter()), ctx,
        adapter_registry=independent_registry(), oracles=apparatus_oracle_registry(),
    )
    out = next(x for x in result.corpus.claims if x.id == c.id)
    if out.status.value != "licensed":
        raise SystemExit(f"HLA claim did not license: status={out.status.value!r}")
    return out


def main() -> None:
    ndmp = _licensed_ndmp_claim()
    hla = _licensed_hla_claim()
    uni = load_corpus(str(_SEED))

    # promote the migrated HLA claim in place (conjectured -> licensed), then add the n-DMP node.
    promoted = tuple(hla if c.id == hla.id else c for c in uni.claims)
    combined = Corpus(
        claims=(*promoted, ndmp),
        defeat_edges=uni.defeat_edges,
        equivalences=uni.equivalences,
        fdr_ledger=uni.fdr_ledger,
    )

    positions = spectral_layout(combined)
    topo = export_topology(combined, layout=Layout.FORCE_DIRECTED, positions=positions)
    stats = frame_stats(
        combined, topo, cycle_index=0, n_frontier=0, n_added=0, n_newly_licensed=1,
    )
    timeline = TopologyTimeline(frames=(TimelineFrame(topology=topo, stats=stats),), n_cycles=0)
    _OUT.write_text(json.dumps(timeline.model_dump(mode="json"), indent=2) + "\n")

    n_lic = sum(1 for c in combined.claims if c.status.value == "licensed")
    print(f"wrote {_OUT} ({len(combined.claims)} nodes, {n_lic} licensed, layout={topo.layout_id})")


if __name__ == "__main__":
    main()
