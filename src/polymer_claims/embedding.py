"""Relational graph embedding (viz v1): a deterministic signed-Laplacian eigenmap over the corpus's
typed conceptual edges, giving each claim a MEANINGFUL 3D position (vs the id-hash force layout).
Umbrella/impure (numpy). The grammar/protocol core never imports this; it is consumed by the viewer
harness and tests. NOT re-exported from polymer_claims.__init__ (keeps the base import numpy-free).
"""
from __future__ import annotations

import hashlib
import math

import numpy as np

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
RHO = 0.3  # polarity attenuation for an opposite-direction rebut pair


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


_FALLBACK_RADIUS = 0.15
_CELL_SPACING = 2.5


def _hash_ball(node_id: str, radius: float = _FALLBACK_RADIUS) -> tuple[float, float, float]:
    """Deterministic position in a small ball from the id hash (for tiny/isolated components)."""
    digest = hashlib.sha256(node_id.encode("utf-8")).digest()
    out = []
    for i in range(3):
        u = int.from_bytes(digest[i * 8 : (i + 1) * 8], "big") / float(2**64)
        out.append(radius * (2.0 * u - 1.0))
    return (out[0], out[1], out[2])


def _components(node_ids: list[str], W: dict[frozenset[str], float]) -> list[list[str]]:
    adj: dict[str, set[str]] = {n: set() for n in node_ids}
    for key in W:
        a, b = tuple(key)
        adj[a].add(b)
        adj[b].add(a)
    seen: set[str] = set()
    comps: list[list[str]] = []
    for n in node_ids:
        if n in seen:
            continue
        stack, comp = [n], []
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            comp.append(x)
            stack.extend(adj[x] - seen)
        comps.append(sorted(comp))
    return comps


def _canonicalize_columns(coords: np.ndarray) -> np.ndarray:
    """Fix each column's sign deterministically and platform-stably: round to 6dp BEFORE choosing
    the pivot, so cross-BLAS float noise (~1e-10) can't flip which entry wins an exact-magnitude
    tie. Flip the column so its largest-|magnitude| (rounded) entry is non-negative; lowest index
    breaks ties on the identical rounded array."""
    out = coords.copy()
    for k in range(out.shape[1]):
        r = np.round(out[:, k], 6)
        j = int(np.argmax(np.abs(r)))
        if r[j] < 0:
            out[:, k] = -out[:, k]
    return out


def _embed_component(
    comp: list[str], W: dict[frozenset[str], float], polar: set[frozenset[str]]
) -> dict[str, tuple[float, float, float]]:
    n = len(comp)
    if n < 4:
        return {nid: _hash_ball(nid) for nid in comp}
    idx = {nid: i for i, nid in enumerate(comp)}
    A = np.zeros((n, n))
    for key, w in W.items():
        a, b = tuple(key)
        if a in idx and b in idx:
            val = w - (RHO if key in polar else 0.0)
            A[idx[a], idx[b]] = val
            A[idx[b], idx[a]] = val
    deg = np.abs(A).sum(axis=1)
    deg[deg == 0] = 1.0
    dinv = 1.0 / np.sqrt(deg)
    L = np.eye(n) - (dinv[:, None] * A * dinv[None, :])
    _, vecs = np.linalg.eigh(L)  # ascending eigenvalues; columns are eigenvectors
    coords = vecs[:, 1:4].copy()  # skip the trivial null component, take the next 3
    coords = _canonicalize_columns(coords)  # platform-stable sign canonicalization
    for k in range(coords.shape[1]):
        m = np.abs(coords[:, k]).max()
        if m > 0:
            coords[:, k] = coords[:, k] / m
    return {nid: tuple(float(v) for v in coords[idx[nid]]) for nid in comp}


def spectral_layout(corpus: Corpus) -> dict[str, tuple[float, float, float]]:
    """Deterministic 3D position per claim from the typed-edge signed-Laplacian eigenmap.

    Per connected component (so unrelated subgraphs separate); components placed on a deterministic
    lattice; sign-canonicalized and rounded → byte-stable. Empty corpus → {}."""
    node_ids, W, polar = build_graph(corpus)
    if not node_ids:
        return {}
    comps = sorted(_components(node_ids, W), key=lambda c: c[0])
    side = max(1, math.ceil(len(comps) ** (1.0 / 3.0)))
    raw: dict[str, tuple[float, float, float]] = {}
    for ci, comp in enumerate(comps):
        local = _embed_component(comp, W, polar)
        gx, gy, gz = ci % side, (ci // side) % side, ci // (side * side)
        ox = (gx - (side - 1) / 2.0) * _CELL_SPACING
        oy = (gy - (side - 1) / 2.0) * _CELL_SPACING
        oz = (gz - (side - 1) / 2.0) * _CELL_SPACING
        for nid, (x, y, z) in local.items():
            raw[nid] = (x + ox, y + oy, z + oz)
    scale = max((abs(v) for xyz in raw.values() for v in xyz), default=1.0) or 1.0
    return {nid: tuple(round(v / scale, 6) for v in xyz) for nid, xyz in raw.items()}


def procrustes_align(
    prev: dict[str, tuple[float, float, float]],
    new: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]]:
    """Orthogonal-Procrustes-align ``new`` spectral positions onto ``prev`` (the previously
    displayed frame) on their common nodes, then apply that single orthogonal transform to ALL
    of ``new``.

    Eigenvectors are defined only up to sign (and rotation within a degenerate eigenspace), so a
    naive per-frame recompute can flip/rotate the whole embedding frame-to-frame. We find the
    orthogonal R (rotation AND reflection — sign-flips are reflections we WANT to undo, so there is
    deliberately NO det-correction) best mapping the new common positions onto the previous ones,
    so consecutive frames differ only by the genuine corpus change.

    Underdetermined (``prev`` empty, or fewer than 2 common ids) → return ``new`` as-is (the frame-0
    reference): callers pass ``spectral_layout`` output, which is already 6dp. The transformed output
    is rounded to 6dp to match ``spectral_layout`` (byte-stable; pins cross-BLAS float noise).
    Deterministic for a fixed input (numpy SVD is deterministic)."""
    common = sorted(prev.keys() & new.keys())
    # Need >=3 correspondences to pin all 3 rotational DOF: with exactly 2, the cross-covariance
    # is rank-1 and SVD resolves the degenerate directions arbitrarily — applying a random
    # rotation to every node (the very frame-thrash this alignment exists to suppress).
    if not prev or len(common) < 3:
        return new

    P = np.array([prev[c] for c in common], dtype=float)  # n x 3 (target, previous frame)
    Q = np.array([new[c] for c in common], dtype=float)    # n x 3 (source, new raw frame)
    p_mean = P.mean(axis=0)
    q_mean = Q.mean(axis=0)
    Pc = P - p_mean
    Qc = Q - q_mean

    M = Qc.T @ Pc                  # 3 x 3
    U, _, Vt = np.linalg.svd(M)
    R = U @ Vt                     # orthogonal, det ±1 — reflection allowed, NO det-correction

    aligned: dict[str, tuple[float, float, float]] = {}
    for nid, xyz in new.items():
        v = (np.array(xyz, dtype=float) - q_mean) @ R + p_mean
        aligned[nid] = tuple(round(float(x), 6) for x in v)
    return aligned
