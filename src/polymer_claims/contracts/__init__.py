"""CES-1: the data seam. A DataHandle.ref resolves (here, against a bundled fixture) to a
frozen, DRS-shaped, content-addressed SEContractRef. The grammar holds only the thin ref string;
all richness lives here, mirroring datasets/load_dataset and profiles/load_profile.

The loader (load_contract) is added in CES-1 Task 4.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from polymer_claims._hashing import canonical_sha256


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AccessMethod(_Frozen):
    type: Literal["file", "https", "s3"]
    access_url: str


class Checksum(_Frozen):
    type: Literal["sha-256"] = "sha-256"
    checksum: str  # hex digest; mirrors GA4GH DRS ChecksumObject.checksum (deliberate shape fidelity)


class SEContractRef(_Frozen):
    # --- SE-Contract / B1 fields ---
    contract_uid: str
    dimnames_hash: str            # canonical content-address: sha256(feature_ids|sample_ids)
    assay: str
    selection: tuple[tuple[str, str], ...] = ()
    genome_assembly: str
    refget_digest: str | None = None
    shared_cause_factors: tuple[str, ...] = ()
    # --- GA4GH DRS shape (fixity) ---
    self_uri: str
    size: int
    checksums: tuple[Checksum, ...]
    access_methods: tuple[AccessMethod, ...]


_DIR = Path(__file__).parent
_contract_root: contextvars.ContextVar[Path | None] = contextvars.ContextVar("_contract_root", default=None)


@contextmanager
def using_contract_root(path):
    """Scope contract resolution to `path` for the duration of the block. Adapters resolve betas via
    the same load_contract, so this reaches them automatically. Default (unset) -> the bundled _DIR
    (byte-identical behavior)."""
    token = _contract_root.set(Path(path))
    try:
        yield
    finally:
        _contract_root.reset(token)


def _resolve_uid(ref: str) -> str:
    """Strip an optional 'se:' scheme prefix; the remainder is the contract uid."""
    return ref[len("se:"):] if ref.startswith("se:") else ref


def load_contract(ref: str) -> SEContractRef:
    """Resolve a DataHandle.ref to a content-addressed SEContractRef. Resolves under the scoped
    contract root (a contextvar, default the bundled dir). Unknown ref -> FileNotFoundError."""
    root = _contract_root.get()
    if root is None:
        root = _DIR
    return _load_contract(_resolve_uid(ref), root)


def load_manifest(se: SEContractRef) -> dict:
    """The `<uid>.json` col_data/manifest sitting beside a contract's betas TSV."""
    betas_path = Path(se.access_methods[0].access_url)
    return json.loads((betas_path.parent / f"{se.contract_uid.split('@')[0]}.json").read_text())


@lru_cache(maxsize=None)
def _load_contract(uid: str, root: Path) -> SEContractRef:
    stem = uid.split("@")[0]
    manifest_path = root / f"{stem}.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"no SE-Contract {uid!r} at {manifest_path}")

    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    assay = manifest["assays"][0]
    betas_path = root / assay["ref"]
    if not betas_path.is_file():  # FIX 2: name the ref instead of a raw OS error on a missing sidecar
        raise FileNotFoundError(f"SE-Contract {uid!r} assay file missing at {betas_path}")
    betas_bytes = betas_path.read_bytes()

    feature_ids = [r["feature_id"] for r in manifest["row_data"]]
    sample_ids = [c["sample_id"] for c in manifest["col_data"]]
    dimnames_hash = canonical_sha256(
        {"feature_ids": feature_ids, "sample_ids": sample_ids}
    )

    fixture_bytes = manifest_bytes + betas_bytes
    checksum = hashlib.sha256(fixture_bytes).hexdigest()

    return SEContractRef(
        contract_uid=manifest["uid"],
        dimnames_hash=dimnames_hash,
        assay=assay["name"],
        # fixture-default grouping selector; manifest-driven when a 2nd fixture needs a different col
        selection=(("group_col", "Sample_Group"),),
        genome_assembly=manifest["metadata"]["genome_assembly"],
        shared_cause_factors=tuple(manifest["metadata"].get("shared_cause_factors", ())),
        self_uri=f"drs://local/{manifest['uid']}",
        size=len(fixture_bytes),
        checksums=(Checksum(checksum=checksum),),
        access_methods=(AccessMethod(type="file", access_url=str(betas_path)),),
    )


def clear_contract_cache() -> None:
    """Drop the bundled-contract lru-cache so the next load_contract re-reads disk
    (a node refresh after a dataset is re-published)."""
    _load_contract.cache_clear()
