"""Local ed25519 DSSE-PAE signing for Polymer attestation/certificate envelopes.

`pae` is pure stdlib. Everything cryptographic goes through `_require_crypto()` so the base install
stays crypto-free — `cryptography` lives only in the [sign] extra. See
docs/superpowers/specs/2026-06-23-dsse-signing-design.md.
"""
from __future__ import annotations


def pae(payload_type: str, body: bytes) -> bytes:
    """DSSE Pre-Authentication Encoding: b"DSSEv1" SP len(type) SP type SP len(body) SP body.
    Single ASCII spaces; lengths are byte counts; type is UTF-8; body is raw bytes."""
    t = payload_type.encode("utf-8")
    return b" ".join(
        [b"DSSEv1", str(len(t)).encode("ascii"), t, str(len(body)).encode("ascii"), body]
    )


def _require_crypto():
    """Import the cryptography pieces lazily; re-raise a friendly hint if the [sign] extra is absent.
    Keeps `name="cryptography"` so callers (the CLI) can branch on it."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "polymer-claims signing needs the [sign] extra: pip install 'polymer-claims[sign]'",
            name="cryptography",
        ) from exc
    return ed25519, serialization, InvalidSignature
