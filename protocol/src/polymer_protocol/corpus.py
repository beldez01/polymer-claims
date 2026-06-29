"""The Corpus (persistent protocol state) + the ephemeral per-cycle products.

Corpus is a pure bundle of existing grammar IR — no new grammar fields. The four
collections are the whole persistent state; everything a cycle computes that is not
itself grammar IR (scaffolding, execution records, frontier, audit) is ephemeral and
returned in CycleResult, never stored — keeping each cycle reversible.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from pydantic import Field, model_validator

from polymer_grammar import (
    Claim,
    DefeatEdge,
    EquivalenceClaim,
    FDRLedger,
    Status,
    StrengthVector,
    VerifiedEvaluation,
)

from .base import _Model
from .ledger import SelectionLedger


def is_locked(claim: Claim) -> bool:
    """A claim is committed/locked iff it carries an anti-HARKing preregistration hash (set by COMMIT).
    The single shared definition — execute/commit/cycle all use this instead of re-expressing it."""
    return claim.provenance is not None and claim.provenance.preregistration_hash is not None


class Corpus(_Model):
    claims: tuple[Claim, ...] = ()
    defeat_edges: tuple[DefeatEdge, ...] = ()
    equivalences: tuple[EquivalenceClaim, ...] = ()
    fdr_ledger: FDRLedger

    def by_id(self) -> Mapping[str, Claim]:
        """Derived id → claim index (not a stored field). Read-only (matches the frozen discipline)."""
        return MappingProxyType({c.id: c for c in self.claims})

    def strength_map(self) -> dict[str, StrengthVector | None]:
        """Derived id → strength vector (the VAF defeat-resolution input)."""
        return {c.id: c.strength for c in self.claims}

    def licensed_ids(self) -> frozenset[str]:
        """The ids of the currently-LICENSED claims (the VAF's accepted set)."""
        return frozenset(c.id for c in self.claims if c.status == Status.LICENSED)

    @model_validator(mode="after")
    def _unique_claim_ids(self) -> "Corpus":
        ids = [c.id for c in self.claims]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"Corpus claim ids must be unique; duplicates: {dupes}")
        return self

    @model_validator(mode="after")
    def _referential_integrity(self) -> "Corpus":
        ids = {c.id for c in self.claims}
        for e in self.defeat_edges:
            if e.target not in ids:
                raise ValueError(f"defeat edge target {e.target!r} is not a claim id")
            # source may be a claim OR a synthetic node id (convention: contains ':')
            if e.source not in ids and ":" not in e.source:
                raise ValueError(f"defeat edge source {e.source!r} is not a claim id")
        for eq in self.equivalences:
            for endpoint in (eq.left, eq.right):
                if endpoint not in ids:
                    raise ValueError(
                        f"equivalence endpoint {endpoint!r} is not a claim id"
                    )
        return self


class CycleScaffolding(_Model):
    """Ephemeral REPRESENT output — argumentation structure, written nowhere."""

    grounded_extension: tuple[str, ...] = ()  # claim ids IN the grounded extension
    frontier: tuple[str, ...] = ()            # unresolved-attack frontier (claim ids)


class ExecRecord(_Model):
    """Bridge from EXECUTE to VERIFY/INTEGRATE: a claim id + its Phase-8 result."""

    claim_id: str
    evaluation: VerifiedEvaluation


class StageAudit(_Model):
    """Human-readable per-stage trace line."""

    stage: str
    note: str
    count: int = Field(default=0, ge=0)


class ValueVector(_Model):
    """Two-axis pursuit value (spec §3.5). Pareto, not a scalar."""

    eig: float = Field(default=0.0, ge=0.0)
    stakes: float = Field(default=0.0, ge=0.0)

    def dominates(self, other: "ValueVector") -> bool:
        ge = self.eig >= other.eig and self.stakes >= other.stakes
        gt = self.eig > other.eig or self.stakes > other.stakes
        return ge and gt


class SelectionDecision(_Model):
    claim_id: str
    selected: bool
    value: ValueVector
    cost: float
    rank: int = Field(default=0, ge=0)
    cell: str = ""
    lane: str = "main"


class SelectionRecord(_Model):
    decisions: tuple[SelectionDecision, ...] = ()
    cardinality: int = Field(default=0, ge=0)


class Proposal(_Model):
    """A candidate from a proposer: a generated claim + any defeat edges it implies."""

    operator_id: str
    claim: Claim
    edges: tuple[DefeatEdge, ...] = ()


class DiscardEntry(_Model):
    operator_id: str
    claim_id: str
    reason: str


class GenerationRecord(_Model):
    proposed: int = Field(default=0, ge=0)
    admitted: tuple[str, ...] = ()
    discarded: tuple[DiscardEntry, ...] = ()


class CycleResult(_Model):
    corpus: Corpus
    frontier: tuple[str, ...] = ()    # next cycle's GENERATE/SELECT target (keystone closure)
    gated_lane: tuple[str, ...] = ()  # claim ids barred from autonomous execution (SAFETY)
    audit: tuple[StageAudit, ...] = ()
    selection: SelectionRecord = SelectionRecord()
    generation: GenerationRecord = GenerationRecord()
    ledger: SelectionLedger = SelectionLedger()
