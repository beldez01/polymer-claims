"""Implementation identity helpers for local adapter registries.

The protocol registry compares implementation hashes, but local adapters should not rely on
hand-written lineage strings. This module derives a stable hash from the adapter class's
`execute` bytecode signature without reading source files.
"""
from __future__ import annotations

import hashlib
import marshal


def implementation_hash_for_adapter(adapter_or_cls: object) -> str:
    """Return a deterministic sha256 digest for an adapter class's execute implementation."""
    cls = adapter_or_cls if isinstance(adapter_or_cls, type) else adapter_or_cls.__class__
    execute = getattr(cls, "execute")
    code = execute.__code__
    payload = (
        f"{cls.__module__}.{cls.__qualname__}".encode(),
        marshal.dumps(code.co_code),
        repr(code.co_consts).encode(),
        repr(code.co_names).encode(),
        repr(code.co_varnames).encode(),
    )
    h = hashlib.sha256()
    for part in payload:
        h.update(len(part).to_bytes(8, "big"))
        h.update(part)
    return "sha256:" + h.hexdigest()
