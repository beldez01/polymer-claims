"""REPRESENTATION RED-TEAM daemon (#5c) — adversarially attack the corpus's REPRESENTATION and propose
a representation-revision fix, as a GenerationAdapter behind the #4b-3 bus.

RepresentationRedTeamAdapter is the deterministic in-package REFERENCE (the TemplateGenerationAdapter
analog for the meta-tier): for each corpus claim it proposes one CONJECTURED claim carrying a
RepresentationRevision flagging that claim's pattern for review. It ships NO real red-teaming
intelligence — real LLM red-teamers implement the same GenerationAdapter Protocol and inject via
bridge_proposer. Belief-neutral (isolated CONJECTURED nodes, no edges); converges (skips its own gen-rt-*
outputs and any existing representation-revision claim). Pure / deterministic.
"""
from __future__ import annotations

from polymer_grammar import (
    CategoricalLeaf,
    Claim,
    PatternTarget,
    RepresentationRevision,
    RevisionOperation,
    Status,
    is_representation_revision,
)

from .corpus import Corpus, Proposal
from .generate import _gen_id
from .generation_adapter import PLACEHOLDER_OPERATOR_ID


class RepresentationRedTeamAdapter:
    """Deterministic reference REPRESENTATION RED-TEAM (a GenerationAdapter). Real intelligence injects."""

    identity = "representation-red-team"

    def propose(self, corpus: Corpus, frontier: tuple[str, ...]) -> tuple[Proposal, ...]:
        props: list[Proposal] = []
        for c in sorted(corpus.claims, key=lambda c: c.id):
            if c.id.startswith("gen-rt-"):
                continue  # convergence: don't red-team own outputs
            if is_representation_revision(c):
                continue  # convergence: don't red-team a representation-revision claim
            cid = _gen_id("rt", c.id)
            revision = RepresentationRevision(
                operation=RevisionOperation.DEPRECATE,
                target=PatternTarget(patterns=(c.pattern,)),
                rationale=f"red-team review of the representation used by {c.id}",
            )
            claim = Claim(
                id=cid,
                title=f"representation review of {c.id}",
                pattern=c.pattern,
                leaves=(CategoricalLeaf(ontology_term=f"red-team-{c.id}"),),
                status=Status.CONJECTURED,
                representation_revision=revision,
            )
            # placeholder operator_id; bridge_proposer forces it to self.identity
            props.append(Proposal(operator_id=PLACEHOLDER_OPERATOR_ID, claim=claim))
        return tuple(props)
