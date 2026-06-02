"""The v1.3 Claim skeleton (spec §3, "The claim object").

Phase 1 wires the foundational primitives: a pattern reference, >=1 L0 leaf, a status
with its lifecycle invariants, and an optional Pareto strength vector. L1 adds the
optional molecular Proposition as `conclusion`. Later phases add the licensing bridge,
L3 defeat edges, L4 revision, and the protocol-imposed provenance fields.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import _Model
from .governance import Governance
from .leaf import Leaf
from .licensing import Licensing
from .operations import EvaluationPlan
from .pattern import PatternRef
from .proposition import Proposition
from .provenance import Provenance
from .roles import CausalRoles
from .status import PendingReason, Status
from .subject import Subject
from .strength import StrengthVector


class Claim(_Model):
    schema_version: Literal["v1.3"] = "v1.3"
    id: str
    title: str
    pattern: PatternRef
    leaves: tuple[Leaf, ...] = Field(min_length=1)
    status: Status
    pending_reason: PendingReason | None = None
    strength: StrengthVector | None = None
    conclusion: Proposition | None = None
    licensing: Licensing | None = None
    roles: CausalRoles | None = None
    subject: Subject | None = None
    provenance: Provenance | None = None
    governance: Governance | None = None
    evaluation_plan: EvaluationPlan | None = None

    @model_validator(mode="after")
    def _pending_reason_iff_pending(self) -> "Claim":
        if self.status == Status.PENDING and self.pending_reason is None:
            raise ValueError("status=PENDING requires a `pending_reason`")
        if self.status != Status.PENDING and self.pending_reason is not None:
            raise ValueError(
                f"`pending_reason` is only valid when status=PENDING; "
                f"got status={self.status.value}"
            )
        return self

    @model_validator(mode="after")
    def _licensing_only_when_licensed(self) -> "Claim":
        if self.licensing is not None and self.status != Status.LICENSED:
            raise ValueError(
                f"`licensing` is only valid when status=LICENSED; "
                f"got status={self.status.value}"
            )
        return self
