"""ATTESTED ingestion (the credence layer) — impure umbrella.

Parses an operator/authority resolutions file, builds one defeasible attested-event claim per
row (forced non-LICENSED), and appends an ATTESTED ResolutionRecord linked to it. Calibration is
an instrument, not a gate: this NEVER runs a cycle and NEVER changes any other claim's status.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Resolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)  # match the repo's immutable-DTO convention

    subject_claim_id: str
    verdict: Literal["upheld", "failed"]
    attestation_ref: str
    resolvability: Literal["resolvable", "unresolvable"] | None = None
    observed_at_cycle: int | None = Field(default=None, ge=0)  # reject negative operator input
    # license_epoch is RECORDED on the ResolutionRecord, not verified against actual epoch state in
    # this slice (epoch-state validation is deferred — §11). The operator declares which licensing
    # episode they assessed; the ingester trusts the value (but rejects negatives).
    license_epoch: int = Field(default=0, ge=0)


def parse_resolutions(text: str) -> list[Resolution]:
    """Parse a JSON array of resolution objects. Raises ValueError on malformed input."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"resolutions file is not valid JSON: {exc}") from exc
    if not isinstance(raw, list):
        raise ValueError("resolutions file must be a JSON array")
    try:
        return [Resolution.model_validate(row) for row in raw]
    except ValidationError as exc:
        raise ValueError(f"invalid resolution row: {exc}") from exc


def validate_against_corpus(res: Resolution, corpus) -> None:
    """The subject must exist and carry a licensing record (earned standing). Distinguishing a
    *historical* license at this epoch from the current one is deferred (needs the epoch ledger)."""
    claim = corpus.by_id().get(res.subject_claim_id)
    if claim is None:
        raise ValueError(f"subject_claim_id {res.subject_claim_id!r} not in corpus")
    if claim.licensing is None:
        raise ValueError(
            f"subject_claim_id {res.subject_claim_id!r} carries no licensing record "
            "(calibration is about earned standing)"
        )
