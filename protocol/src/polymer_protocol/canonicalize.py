"""CANONICALIZE (structural part): collapse structurally-identical claims into one
equivalence class by recording EquivalenceClaim edges.

Records the equivalence relation only — no physical node deletion, no provenance merge
(the grammar's identity philosophy: identity = a licensed equivalence edge, never a
hash/deletion). Semantic/EIG dedup is deferred to SELECT (#3) — spec §6.2. Idempotent.
"""
from __future__ import annotations

from collections import defaultdict

from polymer_grammar import Claim, EquivalenceClaim, Status

from .base import stable_sha
from .corpus import Corpus


def _structural_key(c: Claim) -> str:
    """Stable key over a claim's STRUCTURE: pattern, subject, conclusion, and plan.

    `leaves` are intentionally excluded — they are L0 output slots populated at
    evaluation time; two claims sharing the same pattern/subject/conclusion/plan are
    structurally equivalent regardless of leaf instantiation.
    """
    return stable_sha(
        [
            c.pattern.id,
            c.pattern.version,
            c.subject.model_dump(mode="json") if c.subject is not None else None,
            c.conclusion.content_hash if c.conclusion is not None else None,
            c.evaluation_plan.graph.content_hash if c.evaluation_plan is not None else None,
        ]
    )


def canonicalize(corpus: Corpus) -> Corpus:
    buckets: dict[str, list[str]] = defaultdict(list)
    for c in corpus.claims:
        buckets[_structural_key(c)].append(c.id)

    existing_pairs = {frozenset((eq.left, eq.right)) for eq in corpus.equivalences}
    new_edges: list[EquivalenceClaim] = []
    for ids in buckets.values():
        if len(ids) < 2:
            continue
        ids = sorted(ids)
        rep = ids[0]
        for other in ids[1:]:
            if frozenset((rep, other)) in existing_pairs:
                continue
            new_edges.append(
                EquivalenceClaim(
                    id=f"struct-eq:{rep}:{other}",
                    left=rep,
                    right=other,
                    severity=1.0,  # exact structural identity
                    status=Status.LICENSED,
                    note="structural-key collapse",
                )
            )
    if not new_edges:
        return corpus
    return corpus.model_copy(
        update={"equivalences": corpus.equivalences + tuple(new_edges)}
    )
