from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from polymer_grammar import MaterializationContext


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
        canonical = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


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
