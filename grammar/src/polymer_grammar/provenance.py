"""Provenance — how a claim was generated + the priced implicit search (spec §5 #1).

Without `generated_by` the air-gap / no-self-licensing guarantee can't tell human from
agent; without `search_cardinality` selection-aware significance correction (pricing the
forking paths) is unrepresentable; `preregistration_hash` is the §4 anti-HARKing hash-lock.
The grammar represents; the protocol computes the correction. Imports nothing from
polymer_formalclaim.
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


class Provenance(_Model):
    generated_by: GenerationMode
    agent_id: str | None = None
    method: str | None = None
    version: str | None = None
    search_cardinality: int = Field(ge=1)        # # hypotheses considered to surface this claim
    preregistration_hash: str | None = None      # hash-lock of the primary test (anti-HARKing)

    @model_validator(mode="after")
    def _agent_needs_id(self) -> "Provenance":
        if self.generated_by == GenerationMode.AGENT_GENERATED and self.agent_id is None:
            raise ValueError("generated_by=agent_generated requires an agent_id")
        return self
