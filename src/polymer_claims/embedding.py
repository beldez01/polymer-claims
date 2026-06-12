"""Relational graph embedding (viz v1): a deterministic signed-Laplacian eigenmap over the corpus's
typed conceptual edges, giving each claim a MEANINGFUL 3D position (vs the id-hash force layout).
Umbrella/impure (numpy). The grammar/protocol core never imports this; it is consumed by the viewer
harness and tests. NOT re-exported from polymer_claims.__init__ (keeps the base import numpy-free).
See docs/specs/2026-06-12-relational-graph-embedding-design.md.
"""
from __future__ import annotations

from polymer_grammar import Direction
from polymer_protocol import Layout, export_topology
from polymer_protocol.corpus import Corpus

# Edge kind -> attraction weight (the stated conceptual commitment; see spec §2). incompatible_with
# is deferred to v1.1 (not in the resolved topology edge export yet).
KIND_WEIGHT: dict[str, float] = {
    "equivalence": 1.0,
    "entails": 0.9,
    "evidence_for": 0.8,
    "undermine": 0.5,
    "undercut": 0.5,
    "reclassify": 0.5,
    "reinterpret": 0.5,
    "rebut": 0.4,
}
RHO = 0.3  # polarity repulsion for an opposite-direction rebut pair


def build_graph(
    corpus: Corpus,
) -> tuple[list[str], dict[frozenset[str], float], set[frozenset[str]]]:
    """Return (sorted node ids, weighted adjacency W keyed by unordered pair, polar pair set).

    Edges are sourced from the resolved topology export (entails ∪ equivalence ∪ defeat) so the
    embedding matches the graph the viewer draws. A rebut between opposite-`direction` conclusions
    is flagged polar (gets a repulsion in the eigenmap)."""
    export = export_topology(corpus, layout=Layout.NONE)
    node_ids = sorted(c.id for c in corpus.claims)
    valid = set(node_ids)
    direction_by_id = {
        c.id: (c.conclusion.direction if c.conclusion is not None else None)
        for c in corpus.claims
    }

    W: dict[frozenset[str], float] = {}
    polar: set[frozenset[str]] = set()
    for e in export.edges:
        if e.source == e.target or e.source not in valid or e.target not in valid:
            continue  # skip self-loops and synthetic ':'-source nodes
        w = KIND_WEIGHT.get(e.kind)
        if w is None:
            continue
        key = frozenset((e.source, e.target))
        W[key] = max(W.get(key, 0.0), w)  # strongest relation wins; weak doesn't dilute
        if e.kind == "rebut":
            ds, dt = direction_by_id.get(e.source), direction_by_id.get(e.target)
            if {ds, dt} == {Direction.POSITIVE, Direction.NEGATIVE}:
                polar.add(key)
    return node_ids, W, polar
