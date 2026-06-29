from __future__ import annotations

from dataclasses import asdict, dataclass

from polymer_grammar import MaterializationContext

from .._hashing import canonical_sha256


@dataclass(frozen=True)
class BioNeMoApparatus:
    """Pinned record of WHICH NIM produced evidence: endpoint + model id/version + the
    payload field names. Hashed into MaterializationContext provenance so a certificate
    records the exact NIM. NOT the methylation AnalysisProfile (that schema is array-specific)."""

    endpoint: str
    model_id: str
    model_version: str
    payload_schema: tuple[str, ...]

    def content_hash(self) -> str:
        return canonical_sha256(asdict(self))


def build_materialization_context(
    apparatus: BioNeMoApparatus, *, id: str, api_version: str, data_version: str
) -> MaterializationContext:
    digest = apparatus.content_hash()
    return MaterializationContext(
        id=id,
        api_version=api_version,
        data_version=data_version,
        note=f"bionemo:{apparatus.model_id}@{apparatus.model_version}",
        semantic_run_id=digest,
        profile_hash=digest,
        shared_cause_factors=(f"nim:{apparatus.model_id}@{apparatus.model_version}",),
    )
