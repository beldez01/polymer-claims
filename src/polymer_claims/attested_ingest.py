"""ATTESTED ingestion (the credence layer) — impure umbrella.

Parses an operator/authority resolutions file, builds one defeasible attested-event claim per
row (forced non-LICENSED), and appends an ATTESTED ResolutionRecord linked to it. Calibration is
an instrument, not a gate: this NEVER runs a cycle and NEVER changes any other claim's status.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from polymer_grammar import GenerationMode, Provenance
from polymer_grammar.claim import Claim, Status
from polymer_grammar.leaf import PropositionLeaf
from polymer_grammar.pattern import PatternRef

from ._hashing import canonical_sha256

_ATTEST_PATTERN = PatternRef(id="external-attestation", version="v1")


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


def attested_event_claim(res: Resolution) -> Claim:
    """A defeasible-CAPABLE corpus claim asserting an external authority's determination. CONJECTURED
    and licensing=None => non-LICENSED by construction (the gate never licenses a conjecture, and we
    never call verify on it). It is corpus content that CAN be attacked through the defeat graph, but
    this slice does NOT auto-wire defeat edges between contradictory attestations (deferred — §11).
    Content-addressed id for determinism + idempotency."""
    digest = canonical_sha256({
        "subject": res.subject_claim_id,
        "verdict": res.verdict,
        "ref": res.attestation_ref,
        "epoch": res.license_epoch,
    }).split(":", 1)[1][:16]
    cid = f"attest-{digest}"
    data = (f"external authority {res.attestation_ref} determined that LICENSED claim "
            f"{res.subject_claim_id} is {res.verdict}")
    return Claim(
        id=cid,
        title=f"Attestation: {res.subject_claim_id} {res.verdict}",
        pattern=_ATTEST_PATTERN,
        leaves=(PropositionLeaf(
            data=data,
            warrant="external authority testimony (defeasible, not an oracle)",
            warrant_type="expert_judgment",
        ),),
        status=Status.CONJECTURED,
        provenance=Provenance(
            generated_by=GenerationMode.EXTERNAL_ATTESTATION,
            method=res.attestation_ref,
            search_cardinality=1,
        ),
    )


def inject_attested_event(corpus, claim: Claim):
    """Append the attested-event claim to corpus.claims (no cycle run; no other claim touched).
    Idempotent: if the content-addressed id is already present, return the corpus unchanged."""
    if claim.id in corpus.by_id():
        return corpus
    return corpus.model_copy(update={"claims": (*corpus.claims, claim)})
