"""GENERATE: the proposer bus — the open generation port that closes the flywheel.

Runs passed-in proposers (caller order) + exogenous injections through compile_to_IR and
folds survivors into the corpus. Pure Corpus -> (Corpus, GenerationRecord). Proposers are
the seam where external/LLM proposers plug in later (like the Adapter Protocol). Generated
claims are CONJECTURED/no-plan -> inert this cycle, first act next cycle. Spec §3.
"""
from __future__ import annotations

from collections.abc import Callable

from polymer_grammar import Claim, GenerationMode, Provenance

from .base import stable_sha
from .corpus import Corpus, DiscardEntry, GenerationRecord, Proposal

GEN_ID_PREFIX = "gen"
_ID_HASH_LEN = 16

# A proposer: (corpus, frontier-claim-ids) -> proposals.
Proposer = Callable[[Corpus, tuple[str, ...]], tuple[Proposal, ...]]


def _corpus_fingerprint(corpus: Corpus) -> str:
    """Deterministic fingerprint of the corpus's claim-id set (origin trace)."""
    return stable_sha(sorted(c.id for c in corpus.claims))[:_ID_HASH_LEN]


def _gen_id(operator_short: str, *parts: str) -> str:
    """Content-addressed id for a generated claim — deterministic, collision-resistant."""
    return f"{GEN_ID_PREFIX}-{operator_short}-{stable_sha(list(parts))[:_ID_HASH_LEN]}"


def _ensure_provenance(claim: Claim) -> Claim:
    """Stamp a minimal IMPORTED provenance on an injected claim that lacks one."""
    if claim.provenance is not None:
        return claim
    prov = Provenance(generated_by=GenerationMode.IMPORTED, search_cardinality=1)
    return claim.model_copy(update={"provenance": prov})


def compile_to_IR(proposal: Proposal, present_ids: set[str]) -> str | None:
    """Pressure-sensor: return a discard reason, or None if the proposal is admissible.

    `present_ids` is the live id set (existing + already-admitted this pass)."""
    if proposal.claim.id in present_ids:
        return "duplicate"
    for e in proposal.edges:
        # source must be the proposal's own claim or a synthetic node (convention: ':')
        if e.source != proposal.claim.id and ":" not in e.source:
            return "invalid-edge-source"
        # an edge resolves iff its target is an existing claim or the claim being added
        if e.target not in present_ids and e.target != proposal.claim.id:
            return "unresolved-edge"
    return None


def generate_stage(
    corpus: Corpus,
    frontier: tuple[str, ...],
    *,
    proposers: tuple[Proposer, ...] = (),
    injected: tuple[Claim, ...] = (),
    cap: int | None = None,
) -> tuple[Corpus, GenerationRecord]:
    proposals: list[Proposal] = []
    for prop in proposers:
        proposals.extend(prop(corpus, frontier))
    for claim in injected:
        proposals.append(Proposal(operator_id="exogenous", claim=_ensure_provenance(claim)))

    present_ids = set(corpus.by_id())
    new_claims = list(corpus.claims)
    new_edges = list(corpus.defeat_edges)
    admitted: list[str] = []
    discarded: list[DiscardEntry] = []

    for p in proposals:
        if cap is not None and len(admitted) >= cap:
            discarded.append(DiscardEntry(operator_id=p.operator_id, claim_id=p.claim.id, reason="cap"))
            continue
        reason = compile_to_IR(p, present_ids)
        if reason is not None:
            discarded.append(DiscardEntry(operator_id=p.operator_id, claim_id=p.claim.id, reason=reason))
            continue
        new_claims.append(p.claim)
        new_edges.extend(p.edges)
        present_ids.add(p.claim.id)
        admitted.append(p.claim.id)

    record = GenerationRecord(
        proposed=len(proposals),
        admitted=tuple(sorted(admitted)),
        discarded=tuple(sorted(discarded, key=lambda d: (d.claim_id, d.reason))),
    )
    if not admitted:
        return corpus, record  # identity preserved when nothing folded in
    new_corpus = corpus.model_copy(
        update={"claims": tuple(new_claims), "defeat_edges": tuple(new_edges)}
    )
    return new_corpus, record
