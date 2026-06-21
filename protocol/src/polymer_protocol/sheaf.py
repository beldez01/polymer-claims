"""Cellular-sheaf STRUCTURE extraction over the claims graph (pure, numpy-free).

This module turns a Corpus into a SheafStructure: scalar-ℝ stalks on Quantity-leaf claims,
equivalence edges (agreement) and defeat edges (antagonism, sign-flipped). The numpy spectrum
(energy/H⁰/H¹) lives umbrella-side in polymer_claims.sheaf_spectrum behind the [embed] extra.
Design: docs/superpowers/specs/2026-06-21-sheaf-consistency-gauge-design.md.
"""
from __future__ import annotations

from polymer_grammar import Status

from .base import _Model
from .corpus import Corpus

_DEFAULT_FILTER = frozenset({Status.LICENSED, Status.PENDING})


class SheafVertex(_Model):
    claim_id: str
    value: float
    dimension_sig: tuple[tuple[str, int], ...] | None = None
    unit: str | None = None


class SheafEdge(_Model):
    kind: str          # "equivalence" | "defeat"
    u: str             # equivalence: lower id; defeat: attacker (source)
    v: str             # equivalence: higher id; defeat: target
    weight: float
    sign: int          # +1 equivalence (agreement), -1 defeat (antagonism). d_e = x_u - sign*x_v


class DataQualityFlag(_Model):
    kind: str          # "dimension_mismatch" | "unit_mismatch"
    claim_ids: tuple[str, str]
    detail: str


class SheafStructure(_Model):
    vertices: tuple[SheafVertex, ...] = ()
    edges: tuple[SheafEdge, ...] = ()
    flags: tuple[DataQualityFlag, ...] = ()


def _quantity_leaf(claim):
    for lf in claim.leaves:
        if lf.kind == "quantity":
            return lf
    return None


def extract_sheaf(
    corpus: Corpus,
    *,
    status_filter: frozenset[Status] = _DEFAULT_FILTER,
) -> SheafStructure:
    """Extract a SheafStructure from a Corpus.

    Only Quantity-leaf claims whose status is in ``status_filter`` become vertices.
    Edges and flags are empty after Task 1 (filled by Tasks 2–3).
    """
    vertices: list[SheafVertex] = []
    for c in corpus.claims:
        if c.status not in status_filter:
            continue
        lf = _quantity_leaf(c)
        if lf is None:
            continue
        dim_sig = lf.dimension.exponents if lf.dimension is not None else None
        vertices.append(
            SheafVertex(
                claim_id=c.id,
                value=float(lf.value),
                dimension_sig=dim_sig,
                unit=lf.unit,
            )
        )
    return SheafStructure(vertices=tuple(vertices), edges=(), flags=())
