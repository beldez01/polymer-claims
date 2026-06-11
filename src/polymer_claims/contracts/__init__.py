"""CES-1: the data seam. A DataHandle.ref resolves (here, against a bundled fixture) to a
frozen, DRS-shaped, content-addressed SEContractRef. The grammar holds only the thin ref string;
all richness lives here, mirroring datasets/load_dataset and profiles/load_profile.

The loader (load_contract) is added in CES-1 Task 4.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AccessMethod(_Frozen):
    type: Literal["file", "https", "s3"]
    access_url: str


class Checksum(_Frozen):
    type: Literal["sha-256"] = "sha-256"
    checksum: str  # hex digest


class SEContractRef(_Frozen):
    # --- SE-Contract / B1 fields ---
    contract_uid: str
    dimnames_hash: str            # canonical content-address: sha256(feature_ids|sample_ids)
    assay: str
    selection: tuple[tuple[str, str], ...] = ()
    genome_assembly: str
    refget_digest: str | None = None
    # --- GA4GH DRS shape (fixity) ---
    self_uri: str
    size: int
    checksums: tuple[Checksum, ...]
    access_methods: tuple[AccessMethod, ...]
