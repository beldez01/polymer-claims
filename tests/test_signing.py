import base64

from polymer_claims.attestation import DsseEnvelope
from polymer_claims.signing import (
    generate_keypair, keyid_for, load_private_key, load_public_key,
    pae, serialize_private_pem, serialize_public_pem, sign_envelope, verify_envelope,
)


def test_pae_basic_vector():
    # PAE(type, body) = b"DSSEv1 " + len(type) + " " + type + " " + len(body) + " " + body
    assert pae("X", b"YY") == b"DSSEv1 1 X 2 YY"


def test_pae_lengths_are_byte_counts():
    assert pae("application/vnd.in-toto+json", b"{}") == b"DSSEv1 28 application/vnd.in-toto+json 2 {}"


def test_pae_unicode_type_uses_utf8_byte_length():
    # "é" is 2 UTF-8 bytes, so LEN(type) counts bytes not chars
    assert pae("é", b"") == b"DSSEv1 2 \xc3\xa9 0 "


def _env(body: bytes = b'{"hello":"world"}', ptype: str = "application/vnd.in-toto+json"):
    return DsseEnvelope(payload=base64.b64encode(body).decode("ascii"), **{"payloadType": ptype})


def test_sign_then_verify_roundtrip():
    priv, pub = generate_keypair()
    signed = sign_envelope(_env(), priv)
    assert len(signed.signatures) == 1 and signed.signatures[0].sig
    assert verify_envelope(signed, pub) is True


def test_tampered_payload_fails_verify():
    priv, pub = generate_keypair()
    signed = sign_envelope(_env(), priv)
    tampered = signed.model_copy(update={"payload": base64.b64encode(b'{"hello":"evil"}').decode("ascii")})
    assert verify_envelope(tampered, pub) is False


def test_wrong_key_fails_verify():
    priv, _ = generate_keypair()
    _, other_pub = generate_keypair()
    signed = sign_envelope(_env(), priv)
    assert verify_envelope(signed, other_pub) is False


def test_unsigned_envelope_does_not_verify():
    _, pub = generate_keypair()
    assert verify_envelope(_env(), pub) is False


def test_keyid_is_deterministic_and_key_specific():
    priv, pub = generate_keypair()
    _, other_pub = generate_keypair()
    assert keyid_for(pub) == keyid_for(pub)
    assert keyid_for(pub) != keyid_for(other_pub)
    assert sign_envelope(_env(), priv).signatures[0].keyid == keyid_for(pub)
    assert sign_envelope(_env(), priv, keyid="custom").signatures[0].keyid == "custom"


def test_pem_roundtrip_still_verifies():
    priv, pub = generate_keypair()
    priv2 = load_private_key(serialize_private_pem(priv))
    pub2 = load_public_key(serialize_public_pem(pub))
    signed = sign_envelope(_env(), priv2)
    assert verify_envelope(signed, pub2) is True


def test_pae_binds_certificate_payload_type():
    # Certificate envelopes use a distinct payloadType; PAE must bind it, so a sig made for the
    # certificate type must NOT verify if the type is swapped to the in-toto default.
    priv, pub = generate_keypair()
    env = _env(body=b'{"c":1}', ptype="application/vnd.polymer.certificate+json")
    signed = sign_envelope(env, priv)
    assert signed.payload_type == "application/vnd.polymer.certificate+json"
    assert verify_envelope(signed, pub) is True
    # NOTE: model_copy(update=...) uses FIELD names, not aliases — must be payload_type, not payloadType
    swapped = signed.model_copy(update={"payload_type": "application/vnd.in-toto+json"})
    assert verify_envelope(swapped, pub) is False


def test_keyid_is_informational_not_trusted():
    # A misleading keyid does not change verification — it is by the supplied public key, not keyid.
    priv, pub = generate_keypair()
    signed = sign_envelope(_env(), priv, keyid="totally-wrong-keyid")
    assert verify_envelope(signed, pub) is True


def test_malformed_signature_base64_is_false_not_raise():
    from polymer_claims.attestation import DsseSignature
    _, pub = generate_keypair()
    bad = _env().model_copy(update={"signatures": (DsseSignature(sig="!!!not-base64!!!"),)})
    assert verify_envelope(bad, pub) is False


def test_non_ed25519_pem_is_rejected():
    import pytest
    from cryptography.hazmat.primitives import serialization as _ser
    from cryptography.hazmat.primitives.asymmetric import rsa
    rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = rsa_priv.private_bytes(
        _ser.Encoding.PEM, _ser.PrivateFormat.PKCS8, _ser.NoEncryption()
    )
    pub_pem = rsa_priv.public_key().public_bytes(
        _ser.Encoding.PEM, _ser.PublicFormat.SubjectPublicKeyInfo
    )
    with pytest.raises(ValueError):
        load_private_key(priv_pem)
    with pytest.raises(ValueError):
        load_public_key(pub_pem)


def test_missing_cryptography_is_friendly(monkeypatch):
    import builtins
    import polymer_claims.signing as signing
    real_import = builtins.__import__

    def _no_crypto(name, *a, **k):
        if name.startswith("cryptography"):
            raise ModuleNotFoundError(f"No module named {name!r}", name="cryptography")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _no_crypto)
    import pytest
    with pytest.raises(ModuleNotFoundError) as ei:
        signing.generate_keypair()
    assert ei.value.name == "cryptography"
    assert "[sign]" in str(ei.value)
