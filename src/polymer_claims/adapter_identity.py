"""Implementation identity helpers for local adapter registries.

The protocol registry compares implementation hashes, but local adapters should not rely on
hand-written lineage strings. This module derives a stable hash from a callable's bytecode
signature without reading source files.
"""
from __future__ import annotations

import hashlib
import marshal


def implementation_hash_for_callable(fn: object) -> str:
    """Return a deterministic sha256 digest for any function or method.

    Hashes the callable's bytecode fields (co_code, co_consts, co_names,
    co_varnames) plus its qualname so that:
    - Two distinct callables (different implementations or different names)
      produce different hashes.
    - The same callable always produces the same hash (stable).

    Returns ``"sha256:<hex>"``.
    """
    code = fn.__code__  # type: ignore[attr-defined]
    qualname: str = getattr(fn, "__qualname__", repr(fn))
    payload = (
        qualname.encode(),
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


def implementation_hash_for_adapter(adapter_or_cls: object) -> str:
    """Return a deterministic sha256 digest for an adapter class's execute implementation.

    Delegates to ``implementation_hash_for_callable`` over the class's ``execute``
    method so the two helpers share one hashing algorithm.
    """
    cls = adapter_or_cls if isinstance(adapter_or_cls, type) else adapter_or_cls.__class__
    execute = getattr(cls, "execute")
    return implementation_hash_for_callable(execute)
