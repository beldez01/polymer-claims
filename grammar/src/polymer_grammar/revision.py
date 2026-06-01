"""L4 — AGM/TMS belief revision over the claim corpus (spec §3.5).

Belief-BASE AGM (Hansson): the consequence operation is the L1 inferential-neighborhood
closure (`entails` edges), inconsistency is `incompatible_with`. Entrenchment is a PARTIAL
order from StrengthVector (severity, evidence_against_null) + Status. Consistency
restoration incises the least-entrenched member of each conflict, surfacing robust vs
underdetermined retractions (mirroring blame.py). After any edit, the monotone status
recompute reuses defeat.grounded_extension. Imports nothing from polymer_formalclaim.
"""
from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
from enum import Enum

from .base import _Model
from .claim import Claim
from .defeat import DefeatEdge, derived_rebut_edges, grounded_extension
from .proposition import NeighborEdgeKind
from .status import Status
from .strength import StrengthVector


class Entrench(str, Enum):
    GREATER = "greater"
    LESS = "less"
    EQUAL = "equal"
    INCOMPARABLE = "incomparable"


_STATUS_TIER = {
    Status.REJECTED: 0,
    Status.CONJECTURED: 1,
    Status.EXPLORATORY: 2,
    Status.PENDING: 3,
    Status.LICENSED: 4,
}

_ENTRENCH_AXES = ("severity", "evidence_against_null")


def compare_entrenchment(a: Claim, b: Claim) -> Entrench:
    """Partial entrenchment order (a relative to b). More entrenched = given up last.

    Coarse total tier on Status, then a PARTIAL sub-order on the strength axes
    (severity, evidence_against_null); INCOMPARABLE is a first-class outcome.
    """
    ta, tb = _STATUS_TIER[a.status], _STATUS_TIER[b.status]
    if ta != tb:
        return Entrench.GREATER if ta > tb else Entrench.LESS
    sa, sb = a.strength, b.strength
    if sa is None and sb is None:
        return Entrench.EQUAL
    if sa is None:
        return Entrench.LESS
    if sb is None:
        return Entrench.GREATER
    ge = all(getattr(sa, ax) >= getattr(sb, ax) for ax in _ENTRENCH_AXES)
    le = all(getattr(sa, ax) <= getattr(sb, ax) for ax in _ENTRENCH_AXES)
    if ge and le:
        return Entrench.EQUAL
    if ge:
        return Entrench.GREATER
    if le:
        return Entrench.LESS
    return Entrench.INCOMPARABLE


def entails_closure(seed_hashes: Iterable[str], claims: Iterable[Claim]) -> frozenset[str]:
    """Transitive closure over L1 ENTAILS edges, starting from `seed_hashes`.

    Builds a content_hash -> {entailed content_hashes} graph from every claim's
    conclusion neighborhood, then BFS. Returns the reachable set (incl. the seeds).
    """
    graph: dict[str, set[str]] = defaultdict(set)
    for c in claims:
        if c.conclusion is None:
            continue
        src = c.conclusion.content_hash
        for e in c.conclusion.neighborhood:
            if e.kind == NeighborEdgeKind.ENTAILS:
                graph[src].add(e.target)
    seen = set(seed_hashes)
    queue = deque(seen)
    while queue:
        node = queue.popleft()
        for tgt in graph.get(node, ()):
            if tgt not in seen:
                seen.add(tgt)
                queue.append(tgt)
    return frozenset(seen)


def corpus_entails(claims: Iterable[Claim], prop_hash: str) -> bool:
    """True iff the corpus's conclusions entail `prop_hash` (reachable via ENTAILS)."""
    claims = tuple(claims)
    seeds = {c.conclusion.content_hash for c in claims if c.conclusion is not None}
    return prop_hash in entails_closure(seeds, claims)


def _conflicts(claims: tuple[Claim, ...]) -> list[tuple[Claim, Claim]]:
    """Unordered claim pairs that are mutually incompatible WITHIN the set.

    A conflict exists when one claim's conclusion has an INCOMPATIBLE_WITH edge whose
    target is another present claim's conclusion content_hash.
    """
    by_hash: dict[str, list[Claim]] = defaultdict(list)
    for c in claims:
        if c.conclusion is not None:
            by_hash[c.conclusion.content_hash].append(c)
    pairs: list[tuple[Claim, Claim]] = []
    seen: set[tuple[str, str]] = set()
    for c in claims:
        if c.conclusion is None:
            continue
        for e in c.conclusion.neighborhood:
            if e.kind != NeighborEdgeKind.INCOMPATIBLE_WITH:
                continue
            for other in by_hash.get(e.target, ()):
                if other.id == c.id:
                    continue
                # sorted key: a conflict is unordered — (a, b) and (b, a) are the same
                # pair, so a both-sided incompatibility declaration collapses to one entry.
                key = tuple(sorted((c.id, other.id)))
                if key not in seen:
                    seen.add(key)
                    pairs.append((c, other))
    return pairs


def is_consistent(claims: Iterable[Claim]) -> bool:
    """True iff no INCOMPATIBLE_WITH edge resolves within the claim set."""
    return not _conflicts(tuple(claims))


class RetractionVerdict(_Model):
    robustly_retracted: frozenset[str]   # retracted under EVERY admissible incision
    possibly_retracted: frozenset[str]   # robustly ∪ underdetermined
    underdetermined: frozenset[str]      # incomparable/equal culprits — choice left open
    consistent_core: frozenset[str]      # guaranteed-kept under any admissible choice


class RevisionResult(_Model):
    claims: tuple[Claim, ...]                # the new base (the guaranteed consistent core)
    edges: tuple[DefeatEdge, ...]            # surviving authored edges (those incident to a retracted claim are dropped)
    retraction: RetractionVerdict | None     # present for contract/revise/restore; None for clean expand
    in_set: frozenset[str]                   # grounded_extension over the new base
    flipped_in: frozenset[str]               # newly IN vs prior in_set
    flipped_out: frozenset[str]              # newly OUT vs prior in_set


def _strength_map(claims: tuple[Claim, ...]) -> dict[str, StrengthVector | None]:
    return {c.id: c.strength for c in claims}


def _in_set(claims: tuple[Claim, ...], edges: tuple[DefeatEdge, ...]) -> frozenset[str]:
    """Grounded extension over the base, merging authored edges with derived rebut edges."""
    all_edges = tuple(edges) + derived_rebut_edges(claims)
    return grounded_extension([c.id for c in claims], all_edges, _strength_map(claims))


def _drop_edges_incident_to(
    edges: tuple[DefeatEdge, ...], dropped_ids: frozenset[str]
) -> tuple[DefeatEdge, ...]:
    """Drop authored defeat edges touching a retracted claim. A removed claim must stop
    attacking survivors — otherwise grounded_extension (which injects ANY edge endpoint as
    a node) would let a retracted claim zombie-attack the corpus and wrongly flip a
    survivor OUT. (Synthetic non-claim endpoints like `refutation:*` are unaffected unless
    their target claim was retracted.)"""
    return tuple(
        e for e in edges if e.source not in dropped_ids and e.target not in dropped_ids
    )


def _result(
    new_claims: tuple[Claim, ...],
    edges: tuple[DefeatEdge, ...],
    retraction: RetractionVerdict | None,
    prior_in: frozenset[str],
) -> RevisionResult:
    in_set = _in_set(new_claims, edges)
    return RevisionResult(
        claims=new_claims, edges=tuple(edges), retraction=retraction, in_set=in_set,
        flipped_in=in_set - prior_in, flipped_out=prior_in - in_set,
    )


def restore_consistency(
    claims: Iterable[Claim], edges: Iterable[DefeatEdge], *, prior_in: frozenset[str] | None = None
) -> RevisionResult:
    """Hansson consolidation: make a (possibly inconsistent) base consistent by incising
    the least-entrenched member of each conflict. No claim is privileged. When a conflict's
    members are entrenchment-EQUAL/INCOMPARABLE, both are underdetermined.
    """
    claims = tuple(claims)
    edges = tuple(edges)
    if prior_in is None:
        prior_in = _in_set(claims, edges)
    definite: set[str] = set()
    ambiguous: set[str] = set()
    for a, b in _conflicts(claims):
        cmp = compare_entrenchment(a, b)
        if cmp == Entrench.GREATER:
            definite.add(b.id)
        elif cmp == Entrench.LESS:
            definite.add(a.id)
        else:  # EQUAL or INCOMPARABLE -> either could go
            ambiguous.add(a.id)
            ambiguous.add(b.id)
    robustly = frozenset(definite)
    underdetermined = frozenset(ambiguous - definite)
    possibly = robustly | underdetermined
    core_ids = frozenset(c.id for c in claims) - possibly
    verdict = RetractionVerdict(
        robustly_retracted=robustly, possibly_retracted=possibly,
        underdetermined=underdetermined, consistent_core=core_ids,
    )
    new_claims = tuple(c for c in claims if c.id in core_ids)
    kept_edges = _drop_edges_incident_to(edges, possibly)
    return _result(new_claims, kept_edges, verdict, prior_in)


def expand(claims, edges, new_claim, *, prior_in: frozenset[str] | None = None) -> RevisionResult:
    """AGM expansion: add `new_claim` and recompute. Does NOT restore consistency
    (expansion may yield an inconsistent set — use revise/restore_consistency for that).
    """
    claims = tuple(claims)
    edges = tuple(edges)
    if prior_in is None:
        prior_in = _in_set(claims, edges)
    return _result(claims + (new_claim,), edges, None, prior_in)


def contract(claims, edges, target_id, *, prior_in: frozenset[str] | None = None) -> RevisionResult:
    """AGM contraction: remove `target` and every claim whose conclusion entails target's
    conclusion (single-premise entailment ⇒ all entailers must go — deterministic).
    """
    claims = tuple(claims)
    edges = tuple(edges)
    if prior_in is None:
        prior_in = _in_set(claims, edges)
    target = next((c for c in claims if c.id == target_id), None)
    if target is None or target.conclusion is None:
        verdict = RetractionVerdict(
            robustly_retracted=frozenset(), possibly_retracted=frozenset(),
            underdetermined=frozenset(), consistent_core=frozenset(c.id for c in claims),
        )
        return _result(claims, edges, verdict, prior_in)
    target_hash = target.conclusion.content_hash
    retract = {
        c.id
        for c in claims
        if c.conclusion is not None
        and target_hash in entails_closure({c.conclusion.content_hash}, claims)
    }
    new_claims = tuple(c for c in claims if c.id not in retract)
    verdict = RetractionVerdict(
        robustly_retracted=frozenset(retract), possibly_retracted=frozenset(retract),
        underdetermined=frozenset(), consistent_core=frozenset(c.id for c in new_claims),
    )
    kept_edges = _drop_edges_incident_to(edges, frozenset(retract))
    return _result(new_claims, kept_edges, verdict, prior_in)


def revise(claims, edges, new_claim, *, prior_in: frozenset[str] | None = None) -> RevisionResult:
    """AGM revision via the Levi identity K * p = (K − ¬p) + p, with `new_claim` PRIVILEGED
    (success). Every existing claim incompatible with `new_claim` is retracted (each
    independently conflicts with p, so all must go — deterministic; entrenchment is not
    consulted, and `new_claim` is never a retraction target).
    """
    claims = tuple(claims)
    edges = tuple(edges)
    if prior_in is None:
        prior_in = _in_set(claims, edges)
    np_hash = new_claim.conclusion.content_hash if new_claim.conclusion is not None else None
    incompatible_targets = set()
    if new_claim.conclusion is not None:
        for e in new_claim.conclusion.neighborhood:
            if e.kind == NeighborEdgeKind.INCOMPATIBLE_WITH:
                incompatible_targets.add(e.target)

    def _conflicts_with_new(c: Claim) -> bool:
        if c.conclusion is None:
            return False
        if c.conclusion.content_hash in incompatible_targets:
            return True
        if np_hash is not None:
            return any(
                e.kind == NeighborEdgeKind.INCOMPATIBLE_WITH and e.target == np_hash
                for e in c.conclusion.neighborhood
            )
        return False

    retract = {c.id for c in claims if _conflicts_with_new(c)}
    kept = tuple(c for c in claims if c.id not in retract)
    new_claims = kept + (new_claim,)
    verdict = RetractionVerdict(
        robustly_retracted=frozenset(retract), possibly_retracted=frozenset(retract),
        underdetermined=frozenset(), consistent_core=frozenset(c.id for c in new_claims),
    )
    kept_edges = _drop_edges_incident_to(edges, frozenset(retract))
    return _result(new_claims, kept_edges, verdict, prior_in)
