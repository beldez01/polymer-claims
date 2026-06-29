"""Provenance — how a claim was generated + the priced implicit search (spec §5 #1).

Without `generated_by` the air-gap / no-self-licensing guarantee can't tell human from
agent; without `search_cardinality` selection-aware significance correction (pricing the
forking paths) is unrepresentable; `preregistration_hash` is the §4 anti-HARKing hash-lock.
The grammar represents; the protocol computes the correction. Imports nothing from
polymer_protocol/polymer_claims.
"""
from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from .base import _Model


class GenerationMode(str, Enum):
    HUMAN_AUTHORED = "human_authored"
    AGENT_GENERATED = "agent_generated"
    LITERATURE_EXTRACTED = "literature_extracted"
    MIGRATED = "migrated"
    IMPORTED = "imported"
    EXTERNAL_ATTESTATION = "external_attestation"


class Provenance(_Model):
    generated_by: GenerationMode
    agent_id: str | None = None
    method: str | None = None
    version: str | None = None
    search_cardinality: int = Field(ge=1)        # # hypotheses considered to surface this claim
    preregistration_hash: str | None = None      # hash-lock of the primary test (anti-HARKing)
    # FIRST-PASS rationale surface (2026-06): a free-text justification carried for
    # display only. NOT validated, NOT structured, NOT linked to the corpus claims it
    # builds on. A rigorous extension (structured premises, cited-claim links,
    # anti-hallucination validation, promotion out of Provenance metadata) is future work.
    rationale: str | None = None   # FIRST PASS: opaque free-text "why this claim was proposed"
    # §5a literature-shared-cause: cohort identities (dimnames_hash namespace) that this
    # hypothesis's motivating prior was established on. Empty => no shared-cause info (inert).
    # Operator/agent-asserted (same trust model as adapter independence).
    prior_cohorts: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _agent_needs_id(self) -> Provenance:
        if self.generated_by == GenerationMode.AGENT_GENERATED and self.agent_id is None:
            raise ValueError("generated_by=agent_generated requires an agent_id")
        return self
