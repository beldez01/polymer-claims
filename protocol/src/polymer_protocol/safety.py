"""SAFETY-GATE: bar hazard-flagged claims from autonomous execution.

Uses the grammar's governance predicate. Hazard-flagged claims (high/dual_use) go to the
human-review lane regardless of value; the corpus is returned unchanged (the gate reads
the existing governance posture, writes nothing) — spec §6.3.
"""
from __future__ import annotations

from polymer_grammar import requires_safety_review

from .corpus import Corpus


def safety_gate(corpus: Corpus) -> tuple[Corpus, tuple[str, ...]]:
    gated = tuple(
        sorted(
            c.id
            for c in corpus.claims
            if c.governance is not None and requires_safety_review(c.governance)
        )
    )
    return corpus, gated
