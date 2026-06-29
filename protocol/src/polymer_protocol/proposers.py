"""Pure endogenous proposers for the GENERATE bus (spec §3.2).

rival_generation enriches the rival pool L2 rival_set_closure needs. When the source claim
carries a transplantable evaluation_plan, the rival is emitted as PENDING/UNTESTED carrying a
direction-mirrored (transplanted) plan — making it a real SELECT candidate. Planless sources and
WITHIN_TOL plans (no mirrorable criterion) fall back to CONJECTURED rivals without a plan.
frontier_attack plants belief-neutral candidate-defense SEED claims at unresolved-frontier nodes.
Both operators emit a provisional rebut DefeatEdge alongside each generated claim. The edge is
inert (activate-on-license) while the source claim is CONJECTURED, so belief-neutrality and
corpus convergence are preserved. Both deterministic, both skip their own prior outputs. Spec
§3.2/§3.6.
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    DefeatEdge,
    DefeatEdgeKind,
    Direction,
    GenerationMode,
    PendingReason,
    Provenance,
    Status,
)

from .corpus import Corpus, Proposal
from .generate import _corpus_fingerprint, _gen_id
from .plan_synthesis import transplant_plan

RIVAL_OP = "rival-generation"
FRONTIER_OP = "frontier-attack"


def _generated_by(corpus: Corpus, operator_id: str) -> Provenance:
    return Provenance(
        generated_by=GenerationMode.AGENT_GENERATED,
        agent_id=operator_id,
        method=f"{operator_id}@{_corpus_fingerprint(corpus)}",
        search_cardinality=1,
    )


def _is_own_output(claim: Claim, operator_id: str) -> bool:
    return (
        claim.provenance is not None
        and claim.provenance.method is not None
        and claim.provenance.method.startswith(operator_id)
    )


def rival_generation(corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
    proposals: list[Proposal] = []
    for c in corpus.claims:
        if c.conclusion is None or _is_own_output(c, RIVAL_OP):
            continue
        for d in Direction:
            if d == c.conclusion.direction:
                continue
            rival_concl = c.conclusion.model_copy(update={"direction": d, "neighborhood": ()})
            rid = _gen_id("rival", c.id, d.value)
            transplanted = (
                transplant_plan(c.evaluation_plan) if c.evaluation_plan is not None else None
            )
            base = dict(
                id=rid,
                title=f"rival({d.value}) of {c.id}",
                pattern=c.pattern,
                leaves=c.leaves,
                subject=c.subject,
                conclusion=rival_concl,
                provenance=_generated_by(corpus, RIVAL_OP),
            )
            if transplanted is not None:
                rival = Claim(
                    **base,
                    status=Status.PENDING,
                    pending_reason=PendingReason.UNTESTED,
                    evaluation_plan=transplanted,
                )
            else:
                rival = Claim(**base, status=Status.CONJECTURED)
            edge = DefeatEdge(source=rid, target=c.id, kind=DefeatEdgeKind.REBUT, provisional=True)
            proposals.append(Proposal(operator_id=RIVAL_OP, claim=rival, edges=(edge,)))
    return tuple(proposals)


def frontier_attack(corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
    by_id = corpus.by_id()
    attackers_of: dict[str, list[str]] = {}
    for e in corpus.defeat_edges:
        if ":" in e.source:
            continue  # skip synthetic sources (e.g. refutation:<id>) — not claim-rebuttable
        attackers_of.setdefault(e.target, []).append(e.source)
    proposals: list[Proposal] = []
    for f in frontier:
        for b in attackers_of.get(f, []):
            if b not in by_id:
                continue
            did = _gen_id("fa", f, b)
            d_claim = Claim(
                id=did,
                title=f"challenge to {b}",
                pattern=by_id[b].pattern,
                leaves=(CategoricalLeaf(ontology_term=f"frontier-attack-{b}"),),
                status=Status.CONJECTURED,
                provenance=_generated_by(corpus, FRONTIER_OP),
            )
            edge = DefeatEdge(source=did, target=b, kind=DefeatEdgeKind.REBUT, provisional=True)
            proposals.append(Proposal(operator_id=FRONTIER_OP, claim=d_claim, edges=(edge,)))
    return tuple(proposals)
