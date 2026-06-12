"""export_topology — the pure, deterministic corpus → TopologyExport data contract.

The 3D claim-topology viewer (a SEPARATE instance) consumes this export; this module
owns ONLY the contract (a JSON graph with positions + attributes), never rendering.

Purity: no clock, no random, no IO. Layout positions seed from a stable SHA-256 of each
claim id, so two calls on the same corpus are byte-identical (determinism is a tested
invariant). Grammar is untouched; the Corpus stays its existing 4 collections.
"""
from __future__ import annotations

import hashlib
import math
from enum import Enum

from pydantic import model_validator

from polymer_grammar import (
    AXES,
    NeighborEdgeKind,
    Status,
    effective_defeats,
    is_representation_revision,
)

from .base import _Model
from .corpus import Corpus

# Bump when the topology/timeline wire shape changes incompatibly, so the viewer can
# detect drift against a contract it was built for (audit #10).
CONTRACT_VERSION = "1.0"


class Layout(str, Enum):
    NONE = "none"  # all positions at the origin — for deterministic extraction tests
    FORCE_DIRECTED = "force_directed"  # the real deterministic Fruchterman-Reingold layout


class TopologyNode(_Model):
    id: str
    status: str
    pattern_id: str
    subject_kind: str | None = None
    # When present, the FULL strength vector — exactly len(AXES) floats in AXES order
    # (magnitude, certainty, evidence_against_null, severity, world_contact, explanatory_virtue).
    # The viewer indexes this positionally, so the length/order is a load-bearing contract.
    strength: tuple[float, ...] | None = None
    is_representation_revision: bool = False
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)

    @model_validator(mode="after")
    def _strength_is_full_axis_vector(self) -> "TopologyNode":
        if self.strength is not None and len(self.strength) != len(AXES):
            raise ValueError(
                f"strength must be the full {len(AXES)}-axis vector in AXES order, "
                f"got length {len(self.strength)}"
            )
        return self


class TopologyEdge(_Model):
    source: str
    target: str
    kind: str
    effective: bool
    provisional: bool


class TopologyCluster(_Model):
    id: str
    label: str
    member_ids: tuple[str, ...] = ()


class TopologyExport(_Model):
    nodes: tuple[TopologyNode, ...] = ()
    edges: tuple[TopologyEdge, ...] = ()
    clusters: tuple[TopologyCluster, ...] = ()
    layout_id: str
    contract_version: str = CONTRACT_VERSION


def _effective_set(corpus: Corpus) -> frozenset[tuple[str, str]]:
    """The post-VAF effective-defeat set — computed exactly as represent.py does, so the
    edge `effective` flags mirror the runtime's argumentation state."""
    strength = {c.id: c.strength for c in corpus.claims}
    licensed_ids = frozenset(c.id for c in corpus.claims if c.status == Status.LICENSED)
    return effective_defeats(corpus.defeat_edges, strength, licensed_ids)


def _extract_nodes(
    corpus: Corpus, positions: dict[str, tuple[float, float, float]]
) -> tuple[TopologyNode, ...]:
    nodes = []
    for c in corpus.claims:
        strength = (
            tuple(getattr(c.strength, ax) for ax in AXES)
            if c.strength is not None
            else None
        )
        nodes.append(
            TopologyNode(
                id=c.id,
                status=c.status.value,
                pattern_id=c.pattern.id,
                subject_kind=c.subject.kind if c.subject is not None else None,
                strength=strength,
                is_representation_revision=is_representation_revision(c),
                position=positions.get(c.id, (0.0, 0.0, 0.0)),
            )
        )
    return tuple(sorted(nodes, key=lambda n: n.id))


def _extract_edges(corpus: Corpus) -> tuple[TopologyEdge, ...]:
    eff = _effective_set(corpus)
    edges: list[TopologyEdge] = []

    # defeat edges
    for e in corpus.defeat_edges:
        edges.append(
            TopologyEdge(
                source=e.source,
                target=e.target,
                kind=e.kind.value,
                effective=(e.source, e.target) in eff,
                provisional=e.provisional,
            )
        )

    # equivalences
    for eq in corpus.equivalences:
        edges.append(
            TopologyEdge(
                source=eq.left,
                target=eq.right,
                kind="equivalence",
                effective=True,
                provisional=False,
            )
        )

    # entails — resolve a conclusion's ENTAILS neighborhood target (a content_hash)
    # back to the owning claim id; skip targets that don't resolve.
    hash_to_id: dict[str, str] = {}
    for c in corpus.claims:
        if c.conclusion is not None:
            hash_to_id[c.conclusion.content_hash] = c.id
    for c in corpus.claims:
        if c.conclusion is None:
            continue
        for ne in c.conclusion.neighborhood:
            if ne.kind is not NeighborEdgeKind.ENTAILS:
                continue
            tgt_id = hash_to_id.get(ne.target)
            if tgt_id is None:
                continue
            edges.append(
                TopologyEdge(
                    source=c.id,
                    target=tgt_id,
                    kind="entails",
                    effective=True,
                    provisional=False,
                )
            )

    return tuple(sorted(edges, key=lambda e: (e.source, e.target, e.kind)))


def _extract_clusters(corpus: Corpus) -> tuple[TopologyCluster, ...]:
    by_pattern: dict[str, list[str]] = {}
    for c in corpus.claims:
        by_pattern.setdefault(c.pattern.id, []).append(c.id)
    clusters = [
        TopologyCluster(
            id=f"pattern:{pid}",
            label=f"pattern:{pid}",
            member_ids=tuple(sorted(members)),
        )
        for pid, members in by_pattern.items()
    ]
    return tuple(sorted(clusters, key=lambda cl: cl.id))


_FR_ITERATIONS = 50
_FR_EPSILON = 1e-9
_FR_TEMP = 0.1  # from-scratch initial max displacement; linearly cooled to ~0
# A warm-started frame perturbs only locally: existing nodes start at (near-)equilibrium, so a
# cooler schedule keeps Δposition small (a disconnected node is purely repelled and otherwise
# drifts by ~_FR_TEMP·iters per re-layout — the precision-instrument register, not a lava lamp).
_FR_WARM_TEMP = 0.02


def _seed_position(node_id: str) -> tuple[float, float, float]:
    """Deterministic initial position in [-1, 1]^3 from a stable SHA-256 of the id.
    Three disjoint 8-byte chunks of the digest → three floats. No clock, no random."""
    digest = hashlib.sha256(node_id.encode("utf-8")).digest()
    coords = []
    for i in range(3):
        chunk = digest[i * 8 : (i + 1) * 8]
        u = int.from_bytes(chunk, "big") / float(2**64)  # [0, 1)
        coords.append(2.0 * u - 1.0)  # [-1, 1)
    return (coords[0], coords[1], coords[2])


def _force_directed_layout(
    node_ids: list[str],
    edges: tuple[TopologyEdge, ...],
    seed_positions: dict[str, tuple[float, float, float]] | None = None,
) -> tuple[dict[str, tuple[float, float, float]], str]:
    """Deterministic Fruchterman-Reingold in 3D over the UNDIRECTED adjacency
    (defeat ∪ entails ∪ equivalence). Pure `math`; seeds from id-hashes; fixed
    iterations / ideal length / linear cooling. Positions rounded to 6 dp.

    `seed_positions` warm-starts the layout: an existing node begins from its prior-frame
    position (FR perturbs it locally); a brand-new node falls back to its id-hash seed. The
    `layout_id` records `seed=warm` when any seed positions are supplied (so a frame is
    self-describing); the no-seed path stays byte-identical (`seed=sha256`)."""
    seed_suffix = "warm" if seed_positions else "sha256"
    layout_id = f"fruchterman-reingold:iters={_FR_ITERATIONS},seed={seed_suffix}"
    n = len(node_ids)
    if n == 0:
        return {}, layout_id

    pos = {
        nid: list((seed_positions or {}).get(nid) or _seed_position(nid))
        for nid in node_ids
    }
    if n == 1:
        only = node_ids[0]
        p = pos[only]
        return {only: (round(p[0], 6), round(p[1], 6), round(p[2], 6))}, layout_id

    id_set = set(node_ids)
    # undirected adjacency, de-duplicated, endpoints restricted to real claim ids
    adjacency: set[tuple[str, str]] = set()
    for e in edges:
        if e.source in id_set and e.target in id_set and e.source != e.target:
            adjacency.add((e.source, e.target) if e.source < e.target else (e.target, e.source))

    # FR ideal edge length over a unit-cube-ish area; constant for a given node count
    k = (1.0 / n) ** (1.0 / 3.0)
    t_init = _FR_WARM_TEMP if seed_positions else _FR_TEMP
    t = t_init  # initial max displacement; linearly cooled to ~0

    for step in range(_FR_ITERATIONS):
        disp = {nid: [0.0, 0.0, 0.0] for nid in node_ids}

        # repulsive forces between every pair (k^2 / d)
        for i in range(n):
            vi = node_ids[i]
            pi = pos[vi]
            for j in range(i + 1, n):
                vj = node_ids[j]
                pj = pos[vj]
                dx = pi[0] - pj[0]
                dy = pi[1] - pj[1]
                dz = pi[2] - pj[2]
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                if dist < _FR_EPSILON:
                    dist = _FR_EPSILON
                force = (k * k) / dist
                ux, uy, uz = dx / dist, dy / dist, dz / dist
                disp[vi][0] += ux * force
                disp[vi][1] += uy * force
                disp[vi][2] += uz * force
                disp[vj][0] -= ux * force
                disp[vj][1] -= uy * force
                disp[vj][2] -= uz * force

        # attractive forces along edges (d^2 / k)
        for a, b in adjacency:
            pa = pos[a]
            pb = pos[b]
            dx = pa[0] - pb[0]
            dy = pa[1] - pb[1]
            dz = pa[2] - pb[2]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist < _FR_EPSILON:
                dist = _FR_EPSILON
            force = (dist * dist) / k
            ux, uy, uz = dx / dist, dy / dist, dz / dist
            disp[a][0] -= ux * force
            disp[a][1] -= uy * force
            disp[a][2] -= uz * force
            disp[b][0] += ux * force
            disp[b][1] += uy * force
            disp[b][2] += uz * force

        # limit displacement by temperature, then cool linearly
        for nid in node_ids:
            d = disp[nid]
            dlen = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
            if dlen < _FR_EPSILON:
                continue
            scale = min(dlen, t) / dlen
            p = pos[nid]
            p[0] += d[0] * scale
            p[1] += d[1] * scale
            p[2] += d[2] * scale
        t = t_init * (1.0 - (step + 1) / _FR_ITERATIONS)

    return (
        {nid: (round(p[0], 6), round(p[1], 6), round(p[2], 6)) for nid, p in pos.items()},
        layout_id,
    )


def export_topology(
    corpus: Corpus,
    *,
    layout: Layout,
    seed_positions: dict[str, tuple[float, float, float]] | None = None,
    positions: dict[str, tuple[float, float, float]] | None = None,
) -> TopologyExport:
    """Pure, deterministic corpus → TopologyExport.

    Layout.NONE zeroes every position; FORCE_DIRECTED runs the seeded Fruchterman-Reingold layout.
    `positions` (when supplied) overrides both: each node takes its coordinate from the dict (a
    missing id → origin), `layout_id="external:spectral-v1"`, and `layout`/`seed_positions` are
    ignored — this is the seam an external embedder (e.g. the umbrella spectral layout) injects
    through. Nodes/edges/clusters are sorted for byte-stable output.

    `seed_positions` warm-starts FORCE_DIRECTED from a prior frame's positions; the default-None
    path leaves the no-seed output byte-identical. Determinism: identical inputs → identical output.
    """
    edges = _extract_edges(corpus)
    clusters = _extract_clusters(corpus)
    node_ids = [c.id for c in corpus.claims]

    if positions is not None:
        layout_positions = {cid: positions.get(cid, (0.0, 0.0, 0.0)) for cid in node_ids}
        layout_id = "external:spectral-v1"
    elif layout is Layout.NONE:
        layout_positions = {cid: (0.0, 0.0, 0.0) for cid in node_ids}
        layout_id = "none"
    else:
        layout_positions, layout_id = _force_directed_layout(node_ids, edges, seed_positions)

    nodes = _extract_nodes(corpus, layout_positions)
    return TopologyExport(
        nodes=nodes, edges=edges, clusters=clusters, layout_id=layout_id
    )
