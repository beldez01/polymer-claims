"""JSON manifest schema for reported-stratum synbio claims (the reviewable judgment layer).

One manifest file per compendium chapter, a JSON list of entries. Extraction (this file's
input) is decoupled from construction (`ingest.py`); the manifest is diffable and reviewed
by a human before claims are built. `schema_fit` is mandatory — it feeds the gap ledger.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class _M(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SchemaFit(_M):
    status: str  # "clean" | "gap"
    constraint: str | None = None
    current_ir_behavior: str | None = None
    candidate_resolution: str | None = None
    expansion_class: str | None = None  # general | analysis | subject | domain
    purity_cost: str | None = None


class ManifestLeaf(_M):
    kind: str  # "quantity" | "proposition"
    # quantity
    value: float | None = None
    unit: str | None = None
    uncertainty: float | None = None
    measurement_basis: str | None = None  # "FUNDAMENTAL" | "DERIVED"
    formula: str | None = None
    context: dict | None = None  # {tissue,cell_line,assay,condition}
    # proposition
    data: str | None = None
    warrant: str | None = None
    rebuttal: str | None = None
    warrant_type: str | None = None


class ManifestEntry(_M):
    id: str
    title: str
    tier: int
    skip: bool = False
    topic: str
    leaf: ManifestLeaf
    source: str
    schema_fit: SchemaFit


def load_manifest(path: str | Path) -> list[ManifestEntry]:
    raw = json.loads(Path(path).read_text())
    return [ManifestEntry.model_validate(e) for e in raw]
