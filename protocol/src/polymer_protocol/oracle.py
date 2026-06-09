"""oracle.py — protocol-side oracle policy (spec §6).

The registry (passed into run_cycle like adapters, NEVER persisted in the Corpus) + the
resolution POLICY: an unresolved oracle_ref OR an oracle used outside its qualified domain
counts as effective UNVALIDATED (its validation doesn't apply here). `oracle_cap` returns the
strength to write for a claim after its weakest oracle's ceiling.
"""
from __future__ import annotations

from pydantic import model_validator

from polymer_grammar import (
    Claim,
    OracleDossier,
    StrengthVector,
    Subject,
    ValidationTier,
    cap_strength,
    in_domain,
    referenced_oracle_ids,
    weakest_tier,
)

from .base import _Model


class OracleRegistry(_Model):
    """Execution-environment knowledge of oracle validation. Resolved by id; passed into
    run_cycle, not stored in the Corpus."""

    dossiers: tuple[OracleDossier, ...] = ()

    @model_validator(mode="after")
    def _unique_ids(self) -> "OracleRegistry":
        ids = [d.oracle_id for d in self.dossiers]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"OracleRegistry oracle_ids must be unique; duplicates: {dupes}")
        return self

    def resolve(self, oracle_id: str) -> OracleDossier | None:
        return {d.oracle_id: d for d in self.dossiers}.get(oracle_id)


def _effective_tier(
    registry: OracleRegistry, oracle_id: str, subject: Subject | None
) -> ValidationTier:
    """Resolution policy: unresolved OR out-of-domain -> UNVALIDATED."""
    dossier = registry.resolve(oracle_id)
    if dossier is None:
        return ValidationTier.UNVALIDATED
    if not in_domain(dossier.applicability_domain, subject):
        return ValidationTier.UNVALIDATED
    return dossier.validation_tier


def _tier_for_claim(claim: Claim, registry: OracleRegistry) -> ValidationTier:
    """The weakest effective tier of the oracles the claim's plan references. No plan / no refs
    -> GOLD (the no-constraint identity: GOLD's ceiling is all-1.0, so capping by it is a no-op)."""
    if claim.evaluation_plan is None:
        return ValidationTier.GOLD
    refs = referenced_oracle_ids(claim.evaluation_plan)
    if not refs:
        return ValidationTier.GOLD
    return weakest_tier([_effective_tier(registry, r, claim.subject) for r in refs])


def oracle_cap(claim: Claim, registry: OracleRegistry) -> StrengthVector | None:
    """The strength to write for `claim` after its weakest oracle's ceiling. Returns the
    (possibly unchanged) strength; None only when the claim has no strength to cap."""
    if claim.strength is None:
        return None
    return cap_strength(claim.strength, _tier_for_claim(claim, registry))


def cap_earned(
    strength: StrengthVector, claim: Claim, registry: OracleRegistry
) -> StrengthVector:
    """Cap an EARNED strength (derived in verify_stage, not `claim.strength`) by the claim's
    weakest oracle tier — the recorded-strength step of the earned path (the 2c reconciliation)."""
    return cap_strength(strength, _tier_for_claim(claim, registry))
