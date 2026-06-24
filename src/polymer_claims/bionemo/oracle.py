from __future__ import annotations

from polymer_grammar import ApplicabilityDomain, OracleDossier, ValidationTier
from polymer_protocol import OracleRegistry


def bionemo_oracle_registry(
    *,
    oracle_id: str,
    tier: ValidationTier = ValidationTier.INDIRECT,
    subject_kinds: tuple[str, ...] = (),
    anchor: str | None = None,
) -> OracleRegistry:
    """One-dossier registry capping a BioNeMo-evidenced claim's strength at `tier`.

    Default `INDIRECT`: a pure-compute NIM checked against literature/heuristic values, with
    no direct wet-lab anchor for the subject. NEVER default to ANCHORED/GOLD — those require a
    real bounded wet-lab/clinical anchor. `subject_kinds=()` leaves the domain unbounded.
    """
    return OracleRegistry(
        dossiers=(
            OracleDossier(
                oracle_id=oracle_id,
                validation_tier=tier,
                applicability_domain=ApplicabilityDomain(subject_kinds=subject_kinds),
                anchor=anchor,
            ),
        )
    )
