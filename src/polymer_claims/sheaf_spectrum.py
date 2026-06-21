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
    SheafStructure,
)

_ZERO_TOL = 1e-9    # eigenvalues below this count as the kernel (H⁰)
_ROUND = 6          # 6dp byte-stable output, matching embedding.py


def _coboundary(structure: SheafStructure):
    """Return (idx, x, delta, w, kinds): vertex index map, value vector, coboundary δ (m×n),
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
    return idx, x, delta, w, kinds


def consistency_report(structure: SheafStructure) -> ConsistencyReport:
    idx, x, delta, w, kinds = _coboundary(structure)
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
        h1_obstructions=(),                         # Task 5
        per_claim_tension=tuple(tensions),
        flags=structure.flags,
    )
