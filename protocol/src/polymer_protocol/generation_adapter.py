"""The intelligent-operator seam for GENERATE (#4b slice-3, spec §3-§6).

GenerationAdapter is the injected-intelligence boundary (real LLM/embedding operators implement
it OUTSIDE the package; a deterministic reference ships here). compile_untrusted is the guardrail:
external generation may PROPOSE but never LICENSE — licensing is minted only by the air-gapped
verify, never asserted by an input. Pure, deterministic.
"""
from __future__ import annotations

from typing import Protocol

from polymer_grammar import CategoricalLeaf, Claim, GenerationMode, Provenance, Status

from .corpus import Corpus, Proposal
from .generate import Proposer, _corpus_fingerprint, _gen_id

_ALLOWED = (Status.CONJECTURED, Status.PENDING)

# Reference proposers emit this sentinel operator_id, relying on bridge_proposer to force it to the
# real adapter identity before the proposal reaches any credit-governed path. It must NEVER survive
# bridging — bridge_proposer refuses an adapter that (mis)uses it as an actual identity.
PLACEHOLDER_OPERATOR_ID = "UNSET"


class GenerationAdapter(Protocol):
    """The generation boundary. `identity` becomes the Proposal operator_id (credit-governed)."""

    identity: str

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        ...


def compile_untrusted(
    claim: Claim, identity: str, *, fingerprint: str
) -> tuple[Claim | None, str | None]:
    """Clean+stamp an untrusted claim, or reject it. (cleaned, None) | (None, reason)."""
    if claim.licensing is not None:
        return None, "untrusted-licensing"
    if claim.status not in _ALLOWED:
        return None, "untrusted-status"
    if claim.status == Status.PENDING and claim.evaluation_plan is None:
        return None, "untrusted-status"
    declared = 1
    prov = claim.provenance
    if (
        prov is not None
        and prov.generated_by == GenerationMode.AGENT_GENERATED
        and prov.search_cardinality >= 1
    ):
        declared = prov.search_cardinality
    forced = Provenance(
        generated_by=GenerationMode.AGENT_GENERATED,
        agent_id=identity,
        method=f"{identity}@{fingerprint}",
        search_cardinality=max(1, declared),
        # rationale is benign descriptive free text (no trust/licensing semantics), so
        # preserving an agent-supplied rationale does not weaken propose-not-license.
        rationale=prov.rationale if prov is not None else None,
    )
    return claim.model_copy(update={"provenance": forced}), None


def bridge_proposer(adapters: tuple[GenerationAdapter, ...]) -> Proposer:
    """Wrap injected generation adapters onto the bus as one Proposer: force operator_id to
    each adapter's identity, run compile_untrusted, drop rejected. Plugs into
    run_cycle(proposers=...). Bridge-internal rejections are dropped (not in GenerationRecord;
    compile_untrusted is independently unit-tested)."""
    for a in adapters:
        if a.identity == PLACEHOLDER_OPERATOR_ID:
            raise ValueError(
                f"generation adapter identity may not be the placeholder {PLACEHOLDER_OPERATOR_ID!r} "
                "(it would let the un-forced sentinel reach a credit-governed path)"
            )

    def _proposer(corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        fp = _corpus_fingerprint(corpus)
        out: list[Proposal] = []
        for a in adapters:
            for p in a.propose(corpus, frontier):
                clean, _reason = compile_untrusted(p.claim, a.identity, fingerprint=fp)
                if clean is None:
                    continue
                # C1: coerce every untrusted edge to provisional. An untrusted claim's edge stays
                # inert until the claim itself licenses through the air-gapped verify, so it cannot
                # defeat an honest claim for free (effective_defeats skips unlicensed provisional).
                safe_edges = tuple(e.model_copy(update={"provisional": True}) for e in p.edges)
                out.append(Proposal(operator_id=a.identity, claim=clean, edges=safe_edges))
        return tuple(out)

    return _proposer


class TemplateGenerationAdapter:
    """Deterministic reference GenerationAdapter (the IdentityAdapter analog for generation):
    one CONJECTURED 'elaboration' conjecture per corpus claim (sorted by id, content-addressed).
    Emits no provenance and a placeholder operator_id so the bridge's forcing path is exercised;
    skips its own gen-tmpl-* outputs so the corpus converges. Ships no intelligence."""

    identity = "template-ref"

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        props: list[Proposal] = []
        for c in sorted(corpus.claims, key=lambda c: c.id):
            if c.id.startswith("gen-tmpl-"):
                continue  # convergence guard: don't re-elaborate own outputs
            cid = _gen_id("tmpl", c.id)
            claim = Claim(
                id=cid,
                title=f"elaboration of {c.id}",
                pattern=c.pattern,
                leaves=(CategoricalLeaf(ontology_term=f"template-elaboration-{c.id}"),),
                status=Status.CONJECTURED,
            )
            props.append(Proposal(operator_id=PLACEHOLDER_OPERATOR_ID, claim=claim))
        return tuple(props)
