"""Implementation identity helpers for local adapter registries.

The protocol registry compares implementation hashes, but local adapters should not rely on
hand-written lineage strings. This module derives a stable hash from a callable's bytecode
signature without reading source files.
"""
from __future__ import annotations

import hashlib
import marshal


def _hash_code(identity: str, code: object) -> str:
    """Shared byte-hashing core used by both public helpers.

    Builds a length-prefixed payload from ``identity`` and bytecode fields
    (co_code, co_consts, co_names, co_varnames), sha256s it, and returns
    ``"sha256:<hex>"``.  The identity string is caller-supplied so that
    ``implementation_hash_for_adapter`` can use the *class* module.qualname
    (preserving pre-Task-12 values) while ``implementation_hash_for_callable``
    uses the function/method's own module.qualname.
    """
    payload = (
        identity.encode(),
        marshal.dumps(code.co_code),  # type: ignore[attr-defined]
        repr(code.co_consts).encode(),  # type: ignore[attr-defined]
        repr(code.co_names).encode(),  # type: ignore[attr-defined]
        repr(code.co_varnames).encode(),  # type: ignore[attr-defined]
    )
    h = hashlib.sha256()
    for part in payload:
        h.update(len(part).to_bytes(8, "big"))
        h.update(part)
    return "sha256:" + h.hexdigest()


def implementation_hash_for_callable(fn: object) -> str:
    """Return a deterministic sha256 digest for any function or method.

    Hashes the callable's bytecode fields (co_code, co_consts, co_names,
    co_varnames) plus its ``module.qualname`` so that:
    - Two distinct callables (different implementations or different names)
      produce different hashes.
    - The same callable always produces the same hash (stable).

    Returns ``"sha256:<hex>"``.
    """
    code = fn.__code__  # type: ignore[attr-defined]
    module: str = getattr(fn, "__module__", "") or ""
    qualname: str = getattr(fn, "__qualname__", repr(fn))
    identity = f"{module}.{qualname}" if module else qualname
    return _hash_code(identity, code)


def implementation_hash_for_adapter(adapter_or_cls: object) -> str:
    """Return a deterministic sha256 digest for an adapter class's execute implementation.

    Uses the *class* ``module.qualname`` as the identity string (e.g.
    ``"polymer_claims.exec_adapters.StatsPureAdapter"``) — identical to the
    pre-Task-12 formula — so existing adapter hashes are preserved byte-for-byte.
    Shares the byte-hashing core (``_hash_code``) with
    ``implementation_hash_for_callable`` but keeps a distinct identity string.
    """
    cls = adapter_or_cls if isinstance(adapter_or_cls, type) else adapter_or_cls.__class__
    execute = getattr(cls, "execute")
    identity = f"{cls.__module__}.{cls.__qualname__}"
    return _hash_code(identity, execute.__code__)
