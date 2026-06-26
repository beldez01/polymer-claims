import base64
import json

import pytest

from polymer_claims.cli import main
from tests.attestation._fixtures import corpus_with, licensed_claim, licensing, mc, sat

pytest.importorskip("cryptography")


def _corpus_path(tmp_path):
    corpus = corpus_with(licensed_claim("c1", licensing(sat(mc()))))
    p = tmp_path / "corpus.json"
    p.write_text(corpus.model_dump_json())
    return p


def _keys(tmp_path):
    k, p = tmp_path / "s.key", tmp_path / "s.pub"
    assert main(["keygen", "--key", str(k), "--pub-key", str(p)]) == 0
    return k, p


def _log_pub_pem(logdir, tmp_path):
    # Auto-generated private log key is at logdir/log.key; write its public PEM for pinning.
    from polymer_claims import signing
    priv = signing.load_private_key((logdir / "log.key").read_bytes())
    out = tmp_path / "auto-log.pub"
    out.write_bytes(signing.serialize_public_pem(priv.public_key()))
    return out


def _certify_bundle(tmp_path, capsys, sk, logdir, *extra):
    capsys.readouterr()  # clear prior stderr/stdout (e.g. keygen)
    rc = main(["certify", "c1", "--corpus", str(_corpus_path(tmp_path)), "--format", "dsse",
               "--key", str(sk), "--transparency-log", "--log-dir", str(logdir), *extra])
    return rc, capsys.readouterr()


def test_certify_transparency_log_emits_verifiable_bundle(tmp_path, capsys):
    sk, sp = _keys(tmp_path)
    logdir = tmp_path / "tlog"
    rc, cap = _certify_bundle(tmp_path, capsys, sk, logdir)
    assert rc == 0, cap.err
    bundle = json.loads(cap.out)
    assert bundle["mediaType"] == "application/vnd.polymer.bundle.v0.1+json"
    bpath = tmp_path / "b.json"
    bpath.write_text(cap.out)
    logpub = _log_pub_pem(logdir, tmp_path)
    assert main(["verify-bundle", str(bpath), "--pub-key", str(sp), "--log-pub-key", str(logpub)]) == 0


def test_verify_bundle_untrusted_without_both_keys_returns_2(tmp_path, capsys):
    sk, sp = _keys(tmp_path)
    logdir = tmp_path / "tlog"
    rc, cap = _certify_bundle(tmp_path, capsys, sk, logdir)
    bpath = tmp_path / "b.json"
    bpath.write_text(cap.out)
    assert main(["verify-bundle", str(bpath)]) == 2                         # no pins
    assert main(["verify-bundle", str(bpath), "--pub-key", str(sp)]) == 2   # only one pin -> still untrusted


def test_verify_bundle_tampered_returns_1(tmp_path, capsys):
    sk, sp = _keys(tmp_path)
    logdir = tmp_path / "tlog"
    rc, cap = _certify_bundle(tmp_path, capsys, sk, logdir)
    bundle = json.loads(cap.out)
    bundle["dsseEnvelope"]["payload"] = base64.b64encode(b"tampered").decode("ascii")
    bpath = tmp_path / "b.json"
    bpath.write_text(json.dumps(bundle))
    logpub = _log_pub_pem(logdir, tmp_path)
    assert main(["verify-bundle", str(bpath), "--pub-key", str(sp), "--log-pub-key", str(logpub)]) == 1


def test_rekor_url_is_reserved_not_implemented(tmp_path, capsys):
    sk, _ = _keys(tmp_path)
    rc, cap = _certify_bundle(tmp_path, capsys, sk, tmp_path / "tlog",
                              "--rekor-url", "https://rekor.sigstore.dev")
    assert rc == 1
    assert "not implemented" in cap.err.lower()


def test_certify_keyid_conflicts_with_transparency_log(tmp_path, capsys):
    sk, _ = _keys(tmp_path)
    rc, cap = _certify_bundle(tmp_path, capsys, sk, tmp_path / "tlog", "--keyid", "deadbeef")
    assert rc == 1
    assert "keyid" in cap.err.lower()


def test_certify_without_flag_still_emits_a_bare_verifiable_envelope(tmp_path, capsys):
    # No-regression: with --transparency-log OFF, certify --format dsse must still produce the SAME
    # kind of artifact as before this slice — a bare signed DSSE envelope that verify-dsse accepts,
    # NOT a bundle. (Mirrors the verify-dsse round-trip pattern in tests/test_cli_signing.py.)
    sk, sp = _keys(tmp_path)
    cp = _corpus_path(tmp_path)
    capsys.readouterr()
    assert main(["certify", "c1", "--corpus", str(cp), "--format", "dsse", "--key", str(sk)]) == 0
    out = capsys.readouterr().out
    env = json.loads(out)
    assert "mediaType" not in env                                  # NOT a bundle
    assert set(env) >= {"payloadType", "payload", "signatures"}    # a DSSE envelope
    p = tmp_path / "env.json"
    p.write_text(out)
    assert main(["verify-dsse", str(p), "--pub-key", str(sp)]) == 0  # still valid + verifiable
    # determinism is unchanged too (ed25519 + deterministic render)
    capsys.readouterr()
    assert main(["certify", "c1", "--corpus", str(cp), "--format", "dsse", "--key", str(sk)]) == 0
    assert capsys.readouterr().out == out
