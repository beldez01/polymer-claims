"""Project base model for the v1.3 grammar."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    """Forbid extras so typos in fixtures fail loudly (mirrors formalclaim)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
