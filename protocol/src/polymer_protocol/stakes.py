"""Stakes: the structural leverage of a claim — the size of its forward dependency cone.

If a claim's grounded status flipped, every claim in its cone would need re-evaluation:
claims it attacks (defeat edges, transitively) and claims whose conclusion it entails
(L1 ENTAILS, via the grammar's entails_closure). An honest weighted count — no hidden
scalarization of the strength vector (spec §3.3).
"""
from __future__ import annotations

from polymer_grammar import Status, entails_closure

from .corpus import Corpus

LICENSED_STAKE_WEIGHT = 2.0


def dependency_cone(corpus: Corpus, claim_id: str) -> frozenset[str]:
    by_id = corpus.by_id()
    # forward reachability over defeat edges (source -> target)
    out: dict[str, list[str]] = {}
    for e in corpus.defeat_edges:
        out.setdefault(e.source, []).append(e.target)
    reached: set[str] = set()
    stack = list(out.get(claim_id, []))
    while stack:
        nxt = stack.pop()
        if nxt in reached or nxt == claim_id:
            continue
        reached.add(nxt)
        stack.extend(out.get(nxt, []))
    # entailment cone: claims whose conclusion is entailed by this claim's conclusion
    seed = by_id.get(claim_id)
    if seed is not None and seed.conclusion is not None:
        entailed_hashes = entails_closure([seed.conclusion.content_hash], corpus.claims)
        for c in corpus.claims:
            if c.id != claim_id and c.conclusion is not None and c.conclusion.content_hash in entailed_hashes:
                reached.add(c.id)
    reached.discard(claim_id)
    return frozenset(reached)


def stakes(corpus: Corpus, claim_id: str) -> float:
    by_id = corpus.by_id()
    total = 0.0
    for dep_id in dependency_cone(corpus, claim_id):
        dep = by_id.get(dep_id)
        if dep is not None and dep.status == Status.LICENSED:
            total += LICENSED_STAKE_WEIGHT
        else:
            total += 1.0
    return total
