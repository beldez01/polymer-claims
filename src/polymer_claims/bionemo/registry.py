from __future__ import annotations

from polymer_protocol import AdapterCredential

from polymer_claims.adapter_identity import implementation_hash_for_adapter


def bionemo_credential(
    adapter_cls: type, *, identity: str, owner: str = "NVIDIA", version: str = "v1"
) -> AdapterCredential:
    """Operator-asserted trust metadata for a BioNeMo adapter class. `implementation_hash`
    is derived from the class's `execute` bytecode. PRODUCTION builders here must only ever
    carry real, independently-owned sources — never the synthetic test corroborator."""
    return AdapterCredential(
        identity=identity,
        owner=owner,
        implementation_hash=implementation_hash_for_adapter(adapter_cls),
        version=version,
        trusted=True,
    )
