"""Project base for the protocol runtime.

Re-uses the grammar's frozen-model discipline (one-way dependency: protocol → grammar)
so protocol models share the exact ConfigDict (extra="forbid", frozen, tuples-only).
Also ships the one canonical content-hash helper used by canonicalize/commit.
"""
from __future__ import annotations

import hashlib
import json

from polymer_grammar.base import _Model  # re-export — single source of frozen discipline

__all__ = ["_Model", "stable_sha"]


def stable_sha(obj: object) -> str:
    """Deterministic SHA-256 over a JSON-canonicalized object (sorted keys)."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
