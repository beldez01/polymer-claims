"""The v1.3 Claim skeleton (spec §3, "The claim object").

Phase 1 wires the foundational primitives: a pattern reference, >=1 L0 leaf, a status
with its lifecycle invariants, and an optional Pareto strength vector. Later phases add
the L1 molecular Proposition, the licensing bridge, L3 defeat edges, L4 revision, and
the protocol-imposed provenance fields.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import _Model
from .leaf import Leaf
from .pattern import PatternRef
from .status import PendingReason, Status
from .strength import StrengthVector


class Claim(_Model):
    schema_version: Literal["v1.3"] = "v1.3"
    id: str
    title: str
    pattern: PatternRef
    leaves: list[Leaf] = Field(min_length=1)
    status: Status
    pending_reason: PendingReason | None = None
    strength: StrengthVector | None = None

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
