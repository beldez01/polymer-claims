"""Cross-arm relation proposer — candidate generation (spec `2026-07-13-cross-arm-relations-design.md`
Task 9). Pure-python subject-entity blocking: extract normalized biological keys from a claim's
`Subject`, invert keys -> claim ids, and emit deterministic cross-arm candidate pairs sharing >=1
key. Umbrella module (may import polymer_grammar/polymer_protocol) but this stage needs no numpy.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from polymer_grammar import (
    Claim,
    GeneOrProtein,
    GenomicRegion,
    OntologyTerm,
    PathwayRef,
    RelationKind,
    Tier,
    is_relation,
    make_relation_claim,
)
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


def propose_relations(
    corpus: Corpus, agent: Any, *, max_pairs: int, threshold: float
) -> list[Claim]:
    """Judge every Task-9 candidate pair with `agent.judge(claim_a, claim_b)` and emit a
    CONJECTURED relation `Claim` (via `make_relation_claim`) for judgments clearing `threshold`
    on absolute severity. `agent.judge` returns either `None` (decline) or a dict
    `{"tier", "kind", "severity", "rationale"}`. Every judgment -- emitted or declined, whether
    the agent returned `None` or a below-threshold verdict -- is audit-logged so nothing is
    silent."""
    pairs = candidate_pairs(corpus, max_pairs=max_pairs)
    by_id = corpus.by_id()
    relations: list[Claim] = []
    for a, b in pairs:
        judgment = agent.judge(by_id[a], by_id[b])
        if judgment is None:
            log.info("propose_relations: declined (no judgment) for pair (%s, %s)", a, b)
            continue
        severity = judgment["severity"]
        if abs(severity) < threshold:
            log.info(
                "propose_relations: declined (|severity|=%.3f < threshold=%.3f) for pair "
                "(%s, %s): rationale=%r",
                abs(severity), threshold, a, b, judgment.get("rationale"),
            )
            continue
        relation = make_relation_claim(
            id=f"rel:{a}~{b}",
            source_ids=[a],
            target_ids=[b],
            tier=Tier(judgment["tier"]),
            relation_kind=RelationKind(judgment["kind"]),
            severity=severity,
            rationale=judgment["rationale"],
        )
        log.info(
            "propose_relations: emitted %s for pair (%s, %s): tier=%s kind=%s severity=%.3f",
            relation.id, a, b, judgment["tier"], judgment["kind"], severity,
        )
        relations.append(relation)
    return relations


class LLMRelationAgent:
    """A relation-judging agent whose verdicts come from an injected `complete` (real model
    OUTSIDE the pure core). Mirrors `_GenerationAdapterBase`'s complete/anthropic plumbing
    (`llm_adapter.py`) but judges a *pair* of existing claims instead of generating new ones.

    The real-model path (`.anthropic(...)`) is a live tripwire -- it makes a real network call
    and must never be exercised by a unit test."""

    def __init__(
        self, complete: Callable[[str], str], *, identity: str = "llm-relation-agent"
    ) -> None:
        self.complete = complete
        self.identity = identity

    def judge(self, claim_a: Claim, claim_b: Claim) -> dict[str, Any] | None:
        return self._parse(self.complete(self._build_prompt(claim_a, claim_b)))

    def _build_prompt(self, claim_a: Claim, claim_b: Claim) -> str:
        def describe(c: Claim) -> str:
            concl = getattr(c.conclusion, "descriptor", None)
            return f"- {c.id} [{c.pattern.id}] {c.title}" + (f" :: {concl}" if concl else "")

        schema = (
            '{"tier":"computational|biological","kind":"coheres|tension|restriction_map",'
            '"severity":number,"rationale":str}'
        )
        return (
            "You are a scientific-relation judge comparing two claims drawn from different "
            "arms of a corpus. Decide whether they COHERE, are in TENSION, or one is a "
            "RESTRICTION_MAP of the other. severity is a number in [-1, 1]: positive means "
            "coherence, negative means tension, magnitude is your confidence. If no defensible "
            'relationship exists, decline by returning the literal JSON {"relation": null}. '
            "Otherwise return STRICT JSON ONLY (no prose, no markdown) matching:\n"
            f"{schema}\n\n"
            f"Claim A:\n{describe(claim_a)}\n\nClaim B:\n{describe(claim_b)}\n"
        )

    def _parse(self, raw: str) -> dict[str, Any] | None:
        from .llm_adapter import _extract_json

        obj = _extract_json(raw)
        if obj is None:
            return None  # unparseable -> decline
        if "relation" in obj and obj["relation"] is None:
            return None  # explicit {"relation": null} -> decline
        try:
            tier = str(obj["tier"]).strip()
            kind = str(obj["kind"]).strip()
            severity = float(obj["severity"])
            rationale = str(obj.get("rationale") or "").strip()
            Tier(tier)
            RelationKind(kind)
        except (KeyError, ValueError, TypeError):
            return None
        if not rationale or not (-1.0 <= severity <= 1.0):
            return None
        return {"tier": tier, "kind": kind, "severity": severity, "rationale": rationale}

    @classmethod
    def anthropic(cls, *, model: str = "claude-sonnet-4-6", api_key: str | None = None, **kw):
        """Build an agent backed by the Anthropic SDK (needs the [llm] extra). Lazy import,
        matching `_GenerationAdapterBase.anthropic` -- LIVE TRIPWIRE, exercised via CLI/live-smoke
        only, never by unit tests."""
        try:
            import anthropic
        except ModuleNotFoundError as e:  # pragma: no cover - exercised via CLI, not unit tests
            raise RuntimeError(
                "the LLM relation agent needs the optional extra: pip install 'polymer-claims[llm]'"
            ) from e
        client = anthropic.Anthropic(api_key=api_key)

        def complete(prompt: str) -> str:  # pragma: no cover - real network
            msg = client.messages.create(
                model=model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(getattr(b, "text", "") for b in msg.content)

        return cls(complete, **kw)
