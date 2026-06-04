"""The intelligent-operator seam for GENERATE (#4b slice-3, spec §3-§6).

GenerationAdapter is the injected-intelligence boundary (real LLM/embedding operators implement
it OUTSIDE the package; a deterministic reference ships here). compile_untrusted is the guardrail:
external generation may PROPOSE but never LICENSE — licensing is minted only by the air-gapped
verify, never asserted by an input. Pure, deterministic.
"""
from __future__ import annotations

from typing import Protocol

from polymer_grammar import Claim, GenerationMode, Provenance, Status

from .corpus import Corpus, Proposal

_ALLOWED = (Status.CONJECTURED, Status.PENDING)


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
    )
    return claim.model_copy(update={"provenance": forced}), None
