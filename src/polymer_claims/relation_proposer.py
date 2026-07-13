"""Cross-arm relation proposer — candidate generation (spec `2026-07-13-cross-arm-relations-design.md`
Task 9). Pure-python subject-entity blocking: extract normalized biological keys from a claim's
`Subject`, invert keys -> claim ids, and emit deterministic cross-arm candidate pairs sharing >=1
key. Umbrella module (may import polymer_grammar/polymer_protocol) but this stage needs no numpy.
"""
from __future__ import annotations

import logging

from polymer_grammar import Claim, GeneOrProtein, GenomicRegion, OntologyTerm, PathwayRef, is_relation
from polymer_protocol.corpus import Corpus

log = logging.getLogger(__name__)


def entity_key(claim: Claim) -> frozenset[str]:
    """Normalized biological keys for a claim's subject (empty for `subject is None`).

    Structured identifiers are namespaced (`hgnc:`, `ensembl:`, `uniprot:`, `uri:`, `locus:`,
    `pathway:`) so distinct id spaces never collide. A lowercased-word tokenization of
    `subject.display` is always added too (namespaced `text:`), so plain text-level entity
    overlap (e.g. two claims both mentioning "TP53") is caught even without shared structured ids.
    """
    subject = claim.subject
    if subject is None:
        return frozenset()

    keys: set[str] = set()

    if isinstance(subject, GeneOrProtein):
        ids = subject.identifiers
        if ids.hgnc:
            keys.add(f"hgnc:{ids.hgnc.strip().upper()}")
        if ids.ensembl_gene:
            keys.add(f"ensembl:{ids.ensembl_gene.strip().upper()}")
        if ids.uniprot:
            keys.add(f"uniprot:{ids.uniprot.strip().upper()}")
    elif isinstance(subject, OntologyTerm):
        keys.add(f"uri:{subject.uri.strip()}")
    elif isinstance(subject, GenomicRegion):
        keys.add(f"locus:{subject.assembly}:{subject.chrom}:{subject.start}-{subject.end}")
    elif isinstance(subject, PathwayRef):
        if subject.members is not None and subject.members.uri:
            keys.add(f"pathway:{subject.source}:{subject.members.uri.strip()}")

    display = getattr(subject, "display", None)
    if display:
        for token in display.lower().split():
            token = token.strip(".,;:()[]{}\"'")
            if token:
                keys.add(f"text:{token}")

    return frozenset(keys)


def _arm(claim_id: str) -> str:
    """The merged-universe arm prefix of a claim id (the segment before the first ':')."""
    return claim_id.split(":", 1)[0]


def candidate_pairs(corpus: Corpus, *, max_pairs: int) -> list[tuple[str, str]]:
    """Cross-arm claim-id pairs sharing >=1 `entity_key`, sorted deterministically and capped.

    Relation claims (`is_relation`) are excluded from candidate generation entirely — a relation
    is never proposed about another relation. Pairs are returned as sorted tuples `(min_id,
    max_id)`, deduplicated, in ascending overall order, truncated at `max_pairs`. When truncation
    drops candidates, the dropped count is logged (never silently capped).
    """
    inverted: dict[str, list[str]] = {}
    for claim in corpus.claims:
        if is_relation(claim):
            continue
        for key in entity_key(claim):
            inverted.setdefault(key, []).append(claim.id)

    pairs: set[tuple[str, str]] = set()
    for key in sorted(inverted):
        ids = sorted(set(inverted[key]))
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                if _arm(a) == _arm(b):
                    continue
                pairs.add((a, b) if a < b else (b, a))

    ordered = sorted(pairs)
    if len(ordered) > max_pairs:
        dropped = len(ordered) - max_pairs
        log.warning(
            "candidate_pairs: dropping %d of %d candidate pairs (max_pairs=%d)",
            dropped, len(ordered), max_pairs,
        )
        ordered = ordered[:max_pairs]
    return ordered
