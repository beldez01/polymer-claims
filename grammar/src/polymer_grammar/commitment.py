# grammar/src/polymer_grammar/commitment.py
"""Hypothesis content-hash for the pre-registration ledger (Phase D). A claim's COMMITMENT is its
`evaluation_plan` — the region/graph + criterion (comparator+threshold) + group levels. Pure: stdlib
only; deterministic because models are frozen with tuple collections (canonical JSON)."""
from __future__ import annotations

import hashlib

from .claim import Claim


def commitment_hash(claim: Claim) -> str:
    """Content hash of the claim's evaluation_plan. Raises ValueError if the claim has no plan."""
    if claim.evaluation_plan is None:
        raise ValueError(f"claim {claim.id!r} has no evaluation_plan to commit")
    payload = claim.evaluation_plan.model_dump_json().encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()
