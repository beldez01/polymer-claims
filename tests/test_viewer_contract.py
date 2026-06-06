"""Contract drift guard (audit #10): the committed viewer fixtures the live/sample viewer
consumes MUST still validate against the current protocol DTOs. If a protocol change reshapes
TopologyExport/TopologyTimeline without regenerating the fixtures, this fails loudly instead of
the viewer silently rendering a stale shape."""
from __future__ import annotations

import json
from pathlib import Path

from polymer_protocol import CONTRACT_VERSION, TopologyExport, TopologyTimeline

_PUBLIC = Path(__file__).resolve().parent.parent / "viewer" / "public"


def test_sample_topology_matches_current_contract():
    raw = json.loads((_PUBLIC / "sample-topology.json").read_text())
    export = TopologyExport.model_validate(raw)
    # round-trips through the current model
    assert TopologyExport.model_validate_json(export.model_dump_json()) == export
    assert export.contract_version == CONTRACT_VERSION
    # every present strength is the full axis vector (the load-bearing positional contract)
    assert all(n.strength is None or len(n.strength) == 6 for n in export.nodes)


def test_sample_timeline_matches_current_contract():
    raw = json.loads((_PUBLIC / "sample-timeline.json").read_text())
    timeline = TopologyTimeline.model_validate(raw)
    assert TopologyTimeline.model_validate_json(timeline.model_dump_json()) == timeline
    assert timeline.contract_version == CONTRACT_VERSION
    assert timeline.frames and timeline.frames[0].topology.contract_version == CONTRACT_VERSION
