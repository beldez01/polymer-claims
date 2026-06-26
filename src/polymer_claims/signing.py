"""Local ed25519 DSSE-PAE signing for Polymer attestation/certificate envelopes.

`pae` is pure stdlib. Everything cryptographic goes through `_require_crypto()` so the base install
stays crypto-free — `cryptography` lives only in the [sign] extra. See
docs/superpowers/specs/2026-06-23-dsse-signing-design.md.
"""
from __future__ import annotations

import base64
import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from polymer_claims.attestation import DsseEnvelope


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
    except ImportError as exc:
        raise ModuleNotFoundError(
            "polymer-claims signing needs the [sign] extra: pip install 'polymer-claims[sign]'",
            name="cryptography",
        ) from exc
    return ed25519, serialization, InvalidSignature


def generate_keypair():
    ed25519, _serialization, _inv = _require_crypto()
    priv = ed25519.Ed25519PrivateKey.generate()
    return priv, priv.public_key()


def keyid_for(public_key) -> str:
    _ed, serialization, _inv = _require_crypto()
    der = public_key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return hashlib.sha256(der).hexdigest()[:16]


def sign_envelope(env: DsseEnvelope, private_key, *, keyid: str | None = None) -> DsseEnvelope:
    """Return a NEW envelope signed over PAE(payload_type, decoded payload) — covers exactly the
    bytes in the envelope's payload field. Single-signer by design: REPLACES any existing signatures
    (multi-signer trust policy is deferred, spec §9). `keyid` is an informational identifier, not
    trust-bearing (verification is by an explicitly-supplied public key)."""
    body = base64.b64decode(env.payload)
    raw_sig = private_key.sign(pae(env.payload_type, body))
    kid = keyid if keyid is not None else keyid_for(private_key.public_key())
    from polymer_claims.attestation import DsseSignature
    sig = DsseSignature(sig=base64.b64encode(raw_sig).decode("ascii"), keyid=kid)
    return env.model_copy(update={"signatures": (sig,)})


def verify_envelope(env: DsseEnvelope, public_key) -> bool:
    """True iff >=1 signature verifies against `public_key`. Malformed input (bad base64 in the
    payload or a signature) is treated as non-verifying (returns False, never raises). `keyid` is
    ignored — informational only this slice (spec §9)."""
    _ed, _serialization, InvalidSignature = _require_crypto()
    if not env.signatures:
        return False
    try:
        body = base64.b64decode(env.payload, validate=True)
    except ValueError:
        return False
    msg = pae(env.payload_type, body)
    for s in env.signatures:
        try:
            public_key.verify(base64.b64decode(s.sig, validate=True), msg)
            return True
        except (ValueError, TypeError, InvalidSignature):   # TypeError: a non-Ed25519 key reached here
            continue
    return False


def serialize_private_pem(private_key) -> bytes:
    _ed, serialization, _inv = _require_crypto()
    return private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def serialize_public_pem(public_key) -> bytes:
    _ed, serialization, _inv = _require_crypto()
    return public_key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def serialize_public_der(public_key) -> bytes:
    _ed, serialization, _inv = _require_crypto()
    return public_key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def load_private_key(data: bytes):
    ed25519, serialization, _inv = _require_crypto()
    key = serialization.load_pem_private_key(data, password=None)
    if not isinstance(key, ed25519.Ed25519PrivateKey):   # this slice is Ed25519-only
        raise ValueError(f"not an Ed25519 private key (got {type(key).__name__})")
    return key


def load_public_key(data: bytes):
    ed25519, serialization, _inv = _require_crypto()
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise ValueError(f"not an Ed25519 public key (got {type(key).__name__})")
    return key


def load_public_der(data: bytes):
    ed25519, serialization, _inv = _require_crypto()
    key = serialization.load_der_public_key(data)
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise ValueError(f"not an Ed25519 public key (got {type(key).__name__})")
    return key
