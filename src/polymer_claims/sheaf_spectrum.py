"""Sheaf Laplacian spectrum over a SheafStructure (umbrella/impure: numpy).

Computes the corpus inconsistency energy (Robinson consistency radius), the equivalence/defeat
energy split, dim H⁰, the spectral gap λ₂, per-claim tension, and (Task 5) localized H¹
frustration obstructions. NOT re-exported from polymer_claims.__init__ — base import stays
numpy-free; import lazily. Behind the [embed] extra.
"""
from __future__ import annotations

import numpy as np

from polymer_protocol.sheaf import (
    ClaimTension,
    ConsistencyHeadline,
    ConsistencyReport,
    Obstruction,
    SheafStructure,
    frustration_obstructions,
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


def _spectrum_core(structure: SheafStructure):
    """Shared numpy core. Returns (energy, eq_energy, df_energy, spectral_gap, h0_dim, L, x, total_w).
    Empty/zero-weight → (0.0, 0.0, 0.0, 0.0, n_vertices, None, x, 0.0). Excludes H1 + per-claim tension.

    L is built globally over all vertices; it is block-diagonal across connected components, so energy
    and h0_dim equal a per-component computation. spectral_gap is the global smallest POSITIVE eigenvalue
    — over a disconnected corpus that is the weakest component's algebraic connectivity (each extra
    component adds another kernel eigenvalue counted by h0_dim)."""
    x, delta, w, kinds = _coboundary(structure)
    n = len(structure.vertices)
    total_w = float(w.sum())
    if delta.shape[0] == 0 or total_w == 0.0:
        return 0.0, 0.0, 0.0, 0.0, n, None, x, 0.0, None
    d = delta @ x
    per_edge = w * (d * d)
    raw = float(per_edge.sum())
    eq = float(per_edge[np.array([k == "equivalence" for k in kinds])].sum())
    df = float(per_edge[np.array([k == "defeat" for k in kinds])].sum())
    if abs(eq + df - raw) > 1e-9 * (1.0 + abs(raw)):            # was an assert; raise so -O can't disable it
        raise ValueError(f"energy split does not sum to total: eq={eq}, df={df}, raw={raw}")
    L = delta.T @ (w[:, None] * delta)
    evals = np.linalg.eigvalsh(L)
    h0 = int(np.sum(evals < _ZERO_TOL))
    positive = evals[evals >= _ZERO_TOL]
    gap = float(positive.min()) if positive.size else 0.0
    return raw / total_w, eq / total_w, df / total_w, gap, h0, L, x, total_w, per_edge


def _energy(structure: SheafStructure) -> float:
    """Inconsistency energy only (Robinson radius): O(edges) mat-vec, NO eigendecomposition."""
    x, delta, w, _kinds = _coboundary(structure)
    total_w = float(w.sum())
    if delta.shape[0] == 0 or total_w == 0.0:
        return 0.0
    d = delta @ x
    return float((w * (d * d)).sum()) / total_w


def consistency_headline(structure: SheafStructure) -> ConsistencyHeadline:
    return ConsistencyHeadline(
        inconsistency_energy=round(_energy(structure), _ROUND),
        spectral_gap=None,                 # λ₂ is on-demand only (see consistency_report)
    )


def consistency_report(structure: SheafStructure) -> ConsistencyReport:
    energy, eq, df, gap, h0, L, x, total_w, per_edge = _spectrum_core(structure)
    if L is None:  # empty/zero-weight
        return ConsistencyReport(
            inconsistency_energy=0.0, equivalence_energy=0.0, defeat_energy=0.0,
            spectral_gap=0.0, h0_dim=h0, h1_obstructions=(),
            per_claim_tension=(), flags=structure.flags,
        )
    tensions = _edge_share_tension(structure, total_w, per_edge)
    return ConsistencyReport(
        inconsistency_energy=round(energy, _ROUND),
        equivalence_energy=round(eq, _ROUND),
        defeat_energy=round(df, _ROUND),
        spectral_gap=round(gap, _ROUND),
        h0_dim=h0,
        h1_obstructions=frustration_obstructions(structure),
        per_claim_tension=tensions,
        flags=structure.flags,
    )


def _edge_share_tension(structure: SheafStructure, total_w: float, per_edge) -> tuple[ClaimTension, ...]:
    """Nonnegative per-claim attribution: each edge's w·d² (passed in from _spectrum_core) split
    half to each endpoint. Sums to the inconsistency energy. Defensively skips self-loop/malformed."""
    acc = {v.claim_id: 0.0 for v in structure.vertices}
    for k, e in enumerate(structure.edges):
        if e.u == e.v or e.u not in acc or e.v not in acc:
            continue                                   # self-loop / malformed: should not occur
        share = float(per_edge[k]) / 2.0
        acc[e.u] += share
        acc[e.v] += share
    return tuple(
        ClaimTension(claim_id=v.claim_id, tension=round(acc[v.claim_id] / total_w, _ROUND))
        for v in structure.vertices
    )


