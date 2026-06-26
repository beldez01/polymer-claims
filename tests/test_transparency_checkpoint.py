import base64

import pytest

from polymer_claims import signing
from polymer_claims import transparency as T

pytest.importorskip("cryptography")

ORIGIN = "polymer-claims-local-log"
ROOT = bytes(range(32))
TS = "2026-06-25T00:00:00Z"


def test_body_layout_is_origin_size_b64root_timestamp_then_blank_line():
    body = T.format_checkpoint_body(ORIGIN, 3, ROOT, TS)
    lines = body.split("\n")
    assert lines[0] == ORIGIN
    assert lines[1] == "3"
    assert lines[2] == base64.b64encode(ROOT).decode("ascii")
    assert lines[3] == f"Timestamp: {TS}"
    assert body.endswith("\n\n")  # C2SP: a blank line terminates the signed body


def test_sign_then_verify_round_trip_and_parse():
    priv, pub = signing.generate_keypair()
    note = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    assert "\n— " in note  # contains an em-dash signature line
    assert T.verify_checkpoint(note, pub) is True
    fields = T.parse_checkpoint(note)
    assert fields.origin == ORIGIN
    assert fields.tree_size == 3
    assert fields.root_hash == ROOT
    assert fields.timestamp == TS


def test_verify_fails_on_body_tamper():
    priv, pub = signing.generate_keypair()
    note = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    tampered = note.replace("\n3\n", "\n4\n", 1)  # change tree_size in the signed body
    assert T.verify_checkpoint(tampered, pub) is False


def test_verify_fails_on_signature_tamper():
    priv, pub = signing.generate_keypair()
    note = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    head, sig_line = note.rsplit(" ", 1)
    forged = head + " " + base64.b64encode(b"\x00" * 68).decode("ascii") + "\n"
    assert T.verify_checkpoint(forged, pub) is False


def test_verify_fails_with_wrong_key():
    priv, _ = signing.generate_keypair()
    _, other_pub = signing.generate_keypair()
    note = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    assert T.verify_checkpoint(note, other_pub) is False


def test_verify_fails_on_keyhint_mismatch():
    # Keep the real signature bytes but corrupt the 4-byte keyhint -> must be rejected.
    priv, pub = signing.generate_keypair()
    note = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    head, blob_b64 = note.rstrip("\n").rsplit(" ", 1)
    blob = base64.b64decode(blob_b64, validate=True)
    forged = head + " " + base64.b64encode(b"\xff\xff\xff\xff" + blob[4:]).decode("ascii") + "\n"
    assert T.verify_checkpoint(forged, pub) is False


def test_verify_never_raises_on_malformed():
    _, pub = signing.generate_keypair()
    for junk in ["", "not a checkpoint", "a\nb\nc\n", "— only sig\n"]:
        assert T.verify_checkpoint(junk, pub) is False


def test_verify_rejects_body_without_c2sp_blank_line():
    # A note whose body lacks the mandatory blank line MUST be rejected even if the signature over
    # that (shorter) body is itself valid — C2SP requires the blank-line-terminated body.
    priv, pub = signing.generate_keypair()
    body = f"{ORIGIN}\n3\n{base64.b64encode(ROOT).decode('ascii')}\nTimestamp: {TS}\n"  # single \n, no blank
    blob = base64.b64encode(T._keyhint(ORIGIN, pub) + priv.sign(body.encode("utf-8"))).decode("ascii")
    note = f"{body}— {ORIGIN} {blob}\n"
    assert T.verify_checkpoint(note, pub) is False


def test_signing_is_deterministic_for_fixed_key_and_inputs():
    priv, _ = signing.generate_keypair()
    a = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    b = T.sign_checkpoint(ORIGIN, 3, ROOT, TS, priv)
    assert a == b  # ed25519 is deterministic; fixed inputs -> identical note
