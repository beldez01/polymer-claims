"""TDD test: TopologyNode.shared_cause_overlap — record + export.

Single-cohort claim -> shared_cause_overlap is None (not assessable).
"""
from polymer_protocol.topology import Layout, export_topology

from tests.helpers_verify import licensable_corpus
from polymer_protocol.verify import verify_stage


def test_topology_node_shared_cause_overlap_none_when_single_cohort():
    corpus, scaff, recs = licensable_corpus()
    out = verify_stage(corpus, scaff, recs)
    export = export_topology(out, layout=Layout.NONE)
    n = next(n for n in export.nodes if n.id == "c1")
    assert n.shared_cause_overlap is None  # single cohort -> not assessable
