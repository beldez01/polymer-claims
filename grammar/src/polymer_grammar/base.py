"""Project base model for the v1.3 grammar."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    """Project base: forbid extras (typos fail loudly) and freeze (claims are
    immutable facts — prevents post-construction validator bypass and makes
    models hashable for content-addressing)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, frozen=True)
