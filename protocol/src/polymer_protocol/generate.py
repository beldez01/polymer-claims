"""GENERATE: the proposer bus — the open generation port that closes the flywheel.

Runs passed-in proposers (caller order) + exogenous injections through compile_to_IR and
folds survivors into the corpus. Pure Corpus -> (Corpus, GenerationRecord). Proposers are
the seam where external/LLM proposers plug in later (like the Adapter Protocol). Generated
claims are CONJECTURED/no-plan -> inert this cycle, first act next cycle. Spec §3.

Credit economy (active when ledger + credit_floor + cap all supplied): calls allocate_subcaps
to split the global cap across endogenous operators by prior-cycle SelectionLedger credit.
A proposal whose operator's sub-cap is exhausted is discarded with reason "operator-cap".
Exogenous/injected proposals are EXEMPT — bound only by the global cap. When any of
ledger/credit_floor/cap is None the behavior is byte-identical to the flat-cap mode.
"""
from __future__ import annotations

from collections.abc import Callable

from polymer_grammar import Claim, GenerationMode, Provenance, Status

from .allocate import allocate_subcaps
from .base import stable_sha
from .corpus import Corpus, DiscardEntry, GenerationRecord, Proposal
from .ledger import SelectionLedger

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
    # Trust-boundary backstop (C2): licensing is minted ONLY by the air-gapped verify. No proposal
    # arriving on any port (injected= or proposers=) may carry a licensing block or claim LICENSED
    # — that would smuggle an unverified claim past verify_stage. Rejected before anything else.
    if proposal.claim.licensing is not None:
        return "illicit-licensing"
    if proposal.claim.status == Status.LICENSED:
        return "illicit-status"
    if proposal.claim.id in present_ids:
        return "duplicate"
    for e in proposal.edges:
        # source must be the proposal's own claim or a synthetic node (convention: ':')
        if e.source != proposal.claim.id and ":" not in e.source:
            return "invalid-edge-source"
        # an edge resolves iff its target is an existing claim or the claim being added
        if e.target not in present_ids and e.target != proposal.claim.id:
            return "unresolved-edge"
        # Trust-boundary backstop (C1): an edge sourced from the proposal's OWN (still-unlicensed)
        # claim must be provisional, else it would be immediately effective and defeat an honest
        # claim for free. Synthetic ':'-sourced edges (refutation nodes) are exempt.
        if e.source == proposal.claim.id and not e.provisional:
            return "non-provisional-edge"
    return None


def generate_stage(
    corpus: Corpus,
    frontier: tuple[str, ...],
    *,
    proposers: tuple[Proposer, ...] = (),
    injected: tuple[Claim, ...] = (),
    cap: int | None = None,
    ledger: SelectionLedger | None = None,
    credit_floor: float | None = None,
) -> tuple[Corpus, GenerationRecord]:
    proposals: list[Proposal] = []
    for prop in proposers:
        proposals.extend(prop(corpus, frontier))
    for claim in injected:
        proposals.append(Proposal(operator_id="exogenous", claim=_ensure_provenance(claim)))

    # Credit economy: active only when ledger + credit_floor + cap are all supplied.
    economy_on = ledger is not None and credit_floor is not None and cap is not None
    subcaps: dict[str, int] = {}
    if economy_on:
        endo_ops: list[str] = []
        for p in proposals:
            if p.operator_id != "exogenous" and p.operator_id not in endo_ops:
                endo_ops.append(p.operator_id)
        subcaps = allocate_subcaps(tuple(endo_ops), cap, ledger, floor=credit_floor)  # type: ignore[arg-type]
    op_admitted: dict[str, int] = {}

    present_ids = set(corpus.by_id())
    new_claims = list(corpus.claims)
    new_edges = list(corpus.defeat_edges)
    admitted: list[str] = []
    discarded: list[DiscardEntry] = []

    for p in proposals:
        # Per-operator sub-cap gate (economy mode): reject throttled-operator proposals early
        # so they do not consume global cap slots. Exogenous proposals are EXEMPT.
        if economy_on and p.operator_id != "exogenous":
            if op_admitted.get(p.operator_id, 0) >= subcaps.get(p.operator_id, 0):
                discarded.append(
                    DiscardEntry(operator_id=p.operator_id, claim_id=p.claim.id, reason="operator-cap")
                )
                continue
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
        if p.operator_id != "exogenous":
            op_admitted[p.operator_id] = op_admitted.get(p.operator_id, 0) + 1

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
