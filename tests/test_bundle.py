import base64
import copy

import pytest

from polymer_claims import bundle as B
from polymer_claims import signing
from polymer_claims import transparency as T
from polymer_claims.attestation import DsseEnvelope

pytest.importorskip("cryptography")


def _clock():
    return "2026-06-25T00:00:00Z"


def _make_signed_bundle(tmp_path):
    sig_priv, sig_pub = signing.generate_keypair()
    log_priv, log_pub = signing.generate_keypair()
    env = DsseEnvelope(
        payload_type="application/vnd.polymer.certificate+json",
        payload=base64.b64encode(b'{"claim":"x"}').decode("ascii"),
    )
    env = signing.sign_envelope(env, sig_priv)
    log = T.LocalInclusionLog(tmp_path, log_priv, clock=_clock)
    entry = log.submit(T.canonical_entry_bytes(env))
    b = B.build_bundle(env, sig_pub, entry, log_pub)
    return b, sig_pub, log_pub


def test_build_bundle_shape_and_media_type(tmp_path):
    b, _, _ = _make_signed_bundle(tmp_path)
    assert b["mediaType"] == "application/vnd.polymer.bundle.v0.1+json"
    assert b["mediaType"] != "application/vnd.dev.sigstore.bundle.v0.3+json"  # NOT a Sigstore type
    vm = b["verificationMaterial"]
    assert set(vm) == {"signingKey", "logKey", "inclusion"}
    assert set(vm["signingKey"]) == {"rawBytesDER", "keyHint"}
    assert set(vm["logKey"]) == {"rawBytesDER", "keyHint"}
    assert set(vm["inclusion"]) == {
        "logIndex", "logId", "kindVersion", "integratedTime", "treeSize", "rootHashHex",
        "hashesHex", "checkpoint",
    }
    assert set(b["dsseEnvelope"]) >= {"payloadType", "payload", "signatures"}


def test_build_bundle_rejects_keyid_mismatch(tmp_path):
    sig_priv, sig_pub = signing.generate_keypair()
    log_priv, log_pub = signing.generate_keypair()
    env = DsseEnvelope(payload=base64.b64encode(b"x").decode("ascii"))
    env = signing.sign_envelope(env, sig_priv, keyid="deadbeef")  # NOT keyid_for(sig_pub)
    entry = T.LocalInclusionLog(tmp_path, log_priv, clock=_clock).submit(T.canonical_entry_bytes(env))
    with pytest.raises(ValueError):
        B.build_bundle(env, sig_pub, entry, log_pub)
    assert env.signatures[0].keyid == "deadbeef"  # sanity


def test_verify_trusted_when_both_keys_pinned(tmp_path):
    b, sig_pub, log_pub = _make_signed_bundle(tmp_path)
    r = B.verify_bundle(b, signing_trust_key=sig_pub, log_trust_key=log_pub)
    assert r.status == B.TrustStatus.TRUSTED_VALID
    assert r.envelope_signature_ok and r.inclusion_ok and r.checkpoint_signature_ok
    assert r.signing_key_pinned and r.log_key_pinned and r.reason == ""


def test_verify_untrusted_without_pins(tmp_path):
    b, _, _ = _make_signed_bundle(tmp_path)
    r = B.verify_bundle(b)
    assert r.status == B.TrustStatus.STRUCTURALLY_VALID_UNTRUSTED
    assert r.envelope_signature_ok and r.inclusion_ok and r.checkpoint_signature_ok
    assert not r.signing_key_pinned and not r.log_key_pinned


def test_verify_one_pin_is_not_trusted(tmp_path):
    # Either pin alone leaves the OTHER key merely bundle-embedded -> not a trusted bundle.
    b, sig_pub, log_pub = _make_signed_bundle(tmp_path)
    r_sig_only = B.verify_bundle(b, signing_trust_key=sig_pub)
    r_log_only = B.verify_bundle(b, log_trust_key=log_pub)
    assert r_sig_only.status == B.TrustStatus.STRUCTURALLY_VALID_UNTRUSTED
    assert r_log_only.status == B.TrustStatus.STRUCTURALLY_VALID_UNTRUSTED
    assert r_sig_only.signing_key_pinned and not r_sig_only.log_key_pinned
    assert r_log_only.log_key_pinned and not r_log_only.signing_key_pinned


def test_verify_invalid_when_pinned_key_mismatches(tmp_path):
    b, _, log_pub = _make_signed_bundle(tmp_path)
    _, wrong_pub = signing.generate_keypair()
    r = B.verify_bundle(b, signing_trust_key=wrong_pub, log_trust_key=log_pub)
    assert r.status == B.TrustStatus.INVALID
    assert "signing key" in r.reason.lower()


@pytest.mark.parametrize("mutation", ["payload", "signature", "proof", "ckpt_body", "ckpt_sig",
                                      "signing_key", "log_key", "media_type", "log_id",
                                      "kind_version", "integrated_time"])
def test_verify_invalid_on_each_tamper(tmp_path, mutation):
    b, sig_pub, log_pub = _make_signed_bundle(tmp_path)
    b = copy.deepcopy(b)
    if mutation == "media_type":
        b["mediaType"] = "application/vnd.dev.sigstore.bundle.v0.3+json"
    elif mutation == "log_id":
        b["verificationMaterial"]["inclusion"]["logId"] = "deadbeefdeadbeef"
    elif mutation == "kind_version":
        b["verificationMaterial"]["inclusion"]["kindVersion"] = "dsse/0.0.1"
    elif mutation == "integrated_time":
        b["verificationMaterial"]["inclusion"]["integratedTime"] = "2026-06-25T00:00:00Z"
    elif mutation == "payload":
        b["dsseEnvelope"]["payload"] = base64.b64encode(b"tampered").decode("ascii")
    elif mutation == "signature":
        s = b["dsseEnvelope"]["signatures"][0]["sig"]
        b["dsseEnvelope"]["signatures"][0]["sig"] = base64.b64encode(bytes(64)).decode("ascii") if s else "AA=="
    elif mutation == "proof":
        inc = b["verificationMaterial"]["inclusion"]
        inc["hashesHex"] = (inc["hashesHex"] or ["00" * 32])
        inc["hashesHex"][0] = "11" * 32
    elif mutation == "ckpt_body":
        ck = b["verificationMaterial"]["inclusion"]["checkpoint"]
        b["verificationMaterial"]["inclusion"]["checkpoint"] = ck.replace("\n1\n", "\n2\n", 1)
    elif mutation == "ckpt_sig":
        ck = b["verificationMaterial"]["inclusion"]["checkpoint"]
        head, _ = ck.rsplit(" ", 1)
        b["verificationMaterial"]["inclusion"]["checkpoint"] = head + " " + base64.b64encode(bytes(68)).decode() + "\n"
    elif mutation == "signing_key":
        _, other = signing.generate_keypair()
        b["verificationMaterial"]["signingKey"]["rawBytesDER"] = base64.b64encode(
            signing.serialize_public_der(other)).decode("ascii")
    elif mutation == "log_key":
        _, other = signing.generate_keypair()
        b["verificationMaterial"]["logKey"]["rawBytesDER"] = base64.b64encode(
            signing.serialize_public_der(other)).decode("ascii")
    r = B.verify_bundle(b, signing_trust_key=sig_pub, log_trust_key=log_pub)
    assert r.status == B.TrustStatus.INVALID


def test_verify_never_raises_on_garbage():
    for junk in [{}, {"verificationMaterial": {}}, {"dsseEnvelope": 5}]:
        r = B.verify_bundle(junk)
        assert r.status == B.TrustStatus.INVALID
