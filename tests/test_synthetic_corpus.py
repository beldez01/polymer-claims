from __future__ import annotations

from polymer_grammar import Direction
from polymer_protocol import Layout, export_topology
from polymer_claims._synthetic_corpus import (
    CLUSTERS,
    EQUIV_PAIR,
    ISOLATED,
    POLAR_PAIR,
    planted_corpus,
)


def test_corpus_builds_and_has_three_clusters():
    corpus = planted_corpus()
    ids = {c.id for c in corpus.claims}
    assert len(CLUSTERS) == 3
    for members in CLUSTERS.values():
        assert set(members) <= ids
        assert len(members) >= 6


def test_intra_cluster_edges_dense_inter_sparse():
    corpus = planted_corpus()
    export = export_topology(corpus, layout=Layout.NONE)
    cluster_of = {cid: cl for cl, members in CLUSTERS.items() for cid in members}
    intra = inter = 0
    for e in export.edges:
        ca, cb = cluster_of.get(e.source), cluster_of.get(e.target)
        if ca is None or cb is None:
            continue
        if ca == cb:
            intra += 1
        else:
            inter += 1
    assert intra >= 9          # dense within clusters
    assert inter <= 1          # sparse across clusters


def test_each_cluster_is_one_connected_component():
    import collections
    corpus = planted_corpus()
    export = export_topology(corpus, layout=Layout.NONE)
    adj = collections.defaultdict(set)
    for e in export.edges:
        adj[e.source].add(e.target)
        adj[e.target].add(e.source)
    for cl, members in CLUSTERS.items():
        members = set(members)
        seen = {next(iter(members))}
        stack = list(seen)
        while stack:
            x = stack.pop()
            for y in adj[x]:
                if y in members and y not in seen:
                    seen.add(y)
                    stack.append(y)
        assert seen == members, f"cluster {cl} fragmented: {len(seen)}/{len(members)} reachable"


def test_polar_pair_has_opposite_direction_and_rebut_edge():
    corpus = planted_corpus()
    by_id = {c.id: c for c in corpus.claims}
    a, b = POLAR_PAIR
    da = by_id[a].conclusion.direction
    db = by_id[b].conclusion.direction
    assert {da, db} == {Direction.POSITIVE, Direction.NEGATIVE}
    export = export_topology(corpus, layout=Layout.NONE)
    pairs = {frozenset((e.source, e.target)): e.kind for e in export.edges}
    assert pairs.get(frozenset(POLAR_PAIR)) == "rebut"


def test_equivalence_pair_present():
    corpus = planted_corpus()
    export = export_topology(corpus, layout=Layout.NONE)
    kinds = {frozenset((e.source, e.target)): e.kind for e in export.edges}
    assert kinds.get(frozenset(EQUIV_PAIR)) == "equivalence"


def test_isolated_claims_have_no_edges():
    corpus = planted_corpus()
    export = export_topology(corpus, layout=Layout.NONE)
    touched = {e.source for e in export.edges} | {e.target for e in export.edges}
    for iso in ISOLATED:
        assert iso not in touched
