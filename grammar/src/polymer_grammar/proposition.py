"""L1 — the molecular Proposition (spec §1.1; unified spec §3.2).

A claim's conclusion is molecular (Dummett): typed content PLUS a bounded,
version-pinned inferential neighborhood — its material-incompatibility / consequence
links to other propositions. Identity is NOT the byte-hash (Halvorson 2012); the
hashes below are dedup/cache + neighborhood-version handles only. "Same claim?" is
answered by an asserted, licensed EquivalenceClaim (see equivalence.py), never here.

The neighborhood's incompatible_with / entails edges are *material inference*
(meaning) — distinct from the L3 evidential defeat graph.
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum

from .base import _Model


class Direction(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NULL = "null"


class NeighborEdgeKind(str, Enum):
    INCOMPATIBLE_WITH = "incompatible_with"
    ENTAILS = "entails"


class NeighborEdge(_Model):
    kind: NeighborEdgeKind
    target: str  # content_hash of another Proposition
    label: str | None = None


def _sha(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class Proposition(_Model):
    direction: Direction
    estimand: str
    descriptor: str
    neighborhood: tuple[NeighborEdge, ...] = ()

    @property
    def content_hash(self) -> str:
        """Dedup/cache key over typed content only — NOT identity, NOT neighborhood."""
        return _sha(
            {
                "direction": self.direction.value,
                "estimand": self.estimand,
                "descriptor": self.descriptor,
            }
        )

    @property
    def neighborhood_hash(self) -> str:
        """Order-independent hash pinning the inferential-neighborhood version."""
        edges = sorted(
            (e.kind.value, e.target, e.label or "") for e in self.neighborhood
        )
        return _sha(edges)
