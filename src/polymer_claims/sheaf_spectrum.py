"""Sheaf Laplacian spectrum over a SheafStructure (umbrella/impure: numpy).

Computes the corpus inconsistency energy (Robinson consistency radius), the equivalence/defeat
energy split, dim H⁰, the spectral gap λ₂, per-claim tension, and (Task 5) localized H¹
frustration obstructions. NOT re-exported from polymer_claims.__init__ — base import stays
numpy-free; import lazily. Behind the [embed] extra. Design:
docs/superpowers/specs/2026-06-21-sheaf-consistency-gauge-design.md.
"""
from __future__ import annotations

import numpy as np

from polymer_protocol.sheaf import (
    ClaimTension,
    ConsistencyReport,
    Obstruction,
    SheafStructure,
)

_ZERO_TOL = 1e-9    # eigenvalues below this count as the kernel (H⁰)
_ROUND = 6          # 6dp byte-stable output, matching embedding.py


def _coboundary(structure: SheafStructure):
    """Return (x, delta, w, kinds): value vector, coboundary δ (m×n),
    edge weights, and the per-edge kind list."""
    verts = structure.vertices
    idx = {v.claim_id: i for i, v in enumerate(verts)}
    x = np.array([v.value for v in verts], dtype=float)
    m, n = len(structure.edges), len(verts)
    delta = np.zeros((m, n))
    w = np.zeros(m)
    kinds = []
    for k, e in enumerate(structure.edges):
        delta[k, idx[e.u]] += 1.0
        delta[k, idx[e.v]] += -float(e.sign)        # d_e = x_u - sign*x_v
        w[k] = e.weight
        kinds.append(e.kind)
    return x, delta, w, kinds


def consistency_report(structure: SheafStructure) -> ConsistencyReport:
    x, delta, w, kinds = _coboundary(structure)
    n = len(structure.vertices)
    m = len(structure.edges)
    total_w = float(w.sum())

    if m == 0 or total_w == 0.0:
        # no constraints: perfectly consistent; every vertex is its own consensus dof
        return ConsistencyReport(
            inconsistency_energy=0.0, equivalence_energy=0.0, defeat_energy=0.0,
            spectral_gap=0.0, h0_dim=n, h1_obstructions=(), per_claim_tension=(),
            flags=structure.flags,
        )

    d = delta @ x                                   # per-edge discrepancy
    per_edge = w * (d * d)                          # contribution of each edge to x^T L x
    raw = float(per_edge.sum())
    eq = float(per_edge[np.array([k == "equivalence" for k in kinds])].sum())
    df = float(per_edge[np.array([k == "defeat" for k in kinds])].sum())
    # Exhaustiveness: energy split must account for all edges (catch unknown future kinds)
    assert abs(eq + df - raw) <= 1e-9 * (1.0 + abs(raw)), (
        f"Energy split mismatch: eq={eq} + df={df} != raw={raw}"
    )

    L = delta.T @ (w[:, None] * delta)              # δᵀ W δ
    evals = np.linalg.eigvalsh(L)
    h0_dim = int(np.sum(evals < _ZERO_TOL))
    positive = evals[evals >= _ZERO_TOL]
    spectral_gap = float(positive.min()) if positive.size else 0.0

    Lx = L @ x
    tensions = [
        ClaimTension(claim_id=v.claim_id, tension=round(float(x[i] * Lx[i]) / total_w, _ROUND))
        for i, v in enumerate(structure.vertices)
    ]

    return ConsistencyReport(
        inconsistency_energy=round(raw / total_w, _ROUND),
        equivalence_energy=round(eq / total_w, _ROUND),
        defeat_energy=round(df / total_w, _ROUND),
        spectral_gap=round(spectral_gap, _ROUND),
        h0_dim=h0_dim,
        h1_obstructions=_frustration_obstructions(structure),
        per_claim_tension=tuple(tensions),
        flags=structure.flags,
    )


def _cycle_ids(parent: dict, u: str, v: str) -> list[str]:
    """Tree path v→root and u→root, spliced into the fundamental cycle through edge (u,v)."""
    def up(x: str) -> list[str]:
        path = []
        while x is not None:
            path.append(x)
            x = parent[x]
        return path

    pu, pv = up(u), up(v)
    sv = {p: i for i, p in enumerate(pv)}
    anc = next(p for p in pu if p in sv)            # lowest common ancestor
    left = pu[: pu.index(anc) + 1]                  # u → anc (inclusive)
    right = pv[: sv[anc]]                            # v → (just below anc)
    return left + right[::-1]


def _frustration_obstructions(structure: SheafStructure) -> tuple[Obstruction, ...]:
    """Signed-BFS frustration detection.

    Each vertex gets a label in {+1,-1}; edge (u,v,sign) demands label[v] == sign*label[u].
    A back-edge that violates the running label witnesses a frustrated fundamental cycle
    (tree path u→…→v plus that edge). Deterministic: sorted ids.
    """
    adj: dict[str, list[tuple[str, int, float]]] = {v.claim_id: [] for v in structure.vertices}
    for e in structure.edges:
        adj[e.u].append((e.v, e.sign, e.weight))
        adj[e.v].append((e.u, e.sign, e.weight))    # undirected for balance check

    label: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    obstructions: list[Obstruction] = []
    seen_cycles: set[frozenset[str]] = set()

    for root in sorted(adj):
        if root in label:
            continue
        label[root] = 1
        parent[root] = None
        queue = [root]
        while queue:
            u = queue.pop(0)
            for v, sign, _w in sorted(adj[u]):
                want = sign * label[u]
                if v not in label:
                    label[v] = want
                    parent[v] = u
                    queue.append(v)
                elif label[v] != want:
                    cyc = _cycle_ids(parent, u, v)
                    key = frozenset(cyc)
                    if key not in seen_cycles:
                        seen_cycles.add(key)
                        edges = tuple(
                            (cyc[i], cyc[(i + 1) % len(cyc)]) for i in range(len(cyc))
                        )
                        mag = round(
                            float(sum(e.weight for e in structure.edges if {e.u, e.v} <= key)),
                            _ROUND,
                        )
                        obstructions.append(
                            Obstruction(claim_ids=tuple(cyc), edges=edges, magnitude=mag)
                        )
    return tuple(obstructions)
