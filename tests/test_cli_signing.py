import json

from polymer_claims.cli import main
from tests.attestation._fixtures import corpus_path as _corpus_path


def test_keygen_writes_pem_pair(tmp_path):
    key = tmp_path / "k.key"
    pub = tmp_path / "k.pub"
    rc = main(["keygen", "--key", str(key), "--pub-key", str(pub)])
    assert rc == 0
    assert key.read_bytes().startswith(b"-----BEGIN PRIVATE KEY-----")
    assert pub.read_bytes().startswith(b"-----BEGIN PUBLIC KEY-----")


def test_keygen_refuses_overwrite_without_force(tmp_path, capsys):
    key = tmp_path / "k.key"
    pub = tmp_path / "k.pub"
    assert main(["keygen", "--key", str(key), "--pub-key", str(pub)]) == 0
    rc = main(["keygen", "--key", str(key), "--pub-key", str(pub)])
    assert rc == 1 and "force" in capsys.readouterr().err.lower()
    assert main(["keygen", "--key", str(key), "--pub-key", str(pub), "--force"]) == 0


def test_keygen_filesystem_error_is_rc1_not_traceback(tmp_path, capsys):
    # parent directory does not exist -> the atomic write raises OSError, caught -> rc 1
    rc = main(["keygen", "--key", str(tmp_path / "nope" / "k.key"), "--pub-key", str(tmp_path / "k.pub")])
    assert rc == 1
    assert "Traceback" not in capsys.readouterr().err


def test_verify_dsse_roundtrip(tmp_path):
    import base64

    from polymer_claims.attestation import DsseEnvelope
    from polymer_claims.signing import (
        generate_keypair, serialize_public_pem, sign_envelope,
    )
    priv, pub = generate_keypair()
    env = DsseEnvelope(payload=base64.b64encode(b'{"x":1}').decode("ascii"))
    signed = sign_envelope(env, priv)
    env_path = tmp_path / "env.json"
    env_path.write_text(signed.model_dump_json(by_alias=True, exclude_none=True))
    pub_path = tmp_path / "k.pub"
    pub_path.write_bytes(serialize_public_pem(pub))
    assert main(["verify-dsse", str(env_path), "--pub-key", str(pub_path)]) == 0
    # tamper -> rc 1
    bad = json.loads(env_path.read_text())
    bad["payload"] = base64.b64encode(b'{"x":2}').decode("ascii")
    env_path.write_text(json.dumps(bad))
    assert main(["verify-dsse", str(env_path), "--pub-key", str(pub_path)]) == 1


def test_verify_dsse_malformed_inputs_return_rc1_not_traceback(tmp_path, capsys):
    from polymer_claims.signing import generate_keypair, serialize_public_pem
    _, pub = generate_keypair()
    pub_path = tmp_path / "k.pub"
    pub_path.write_bytes(serialize_public_pem(pub))
    # not-a-DSSE-envelope JSON
    p = tmp_path / "junk.json"
    p.write_text('{"not":"an envelope"}')
    assert main(["verify-dsse", str(p), "--pub-key", str(pub_path)]) == 1
    # not JSON at all
    p.write_text("this is not json")
    assert main(["verify-dsse", str(p), "--pub-key", str(pub_path)]) == 1
    # malformed public key
    badpub = tmp_path / "bad.pub"
    badpub.write_text("-----BEGIN PUBLIC KEY-----\nnope\n-----END PUBLIC KEY-----\n")
    p.write_text('{"payload":"e30=","payloadType":"application/vnd.in-toto+json","signatures":[]}')
    assert main(["verify-dsse", str(p), "--pub-key", str(badpub)]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_certify_dsse_unsigned_is_byte_identical(tmp_path, capsys):
    cp = _corpus_path(tmp_path)
    rc = main(["certify", "c1", "--corpus", str(cp), "--format", "dsse", "--q", "0.05"])
    assert rc == 0
    cli_out = capsys.readouterr().out
    # direct pre-slice render (certify default --q is 0.05)
    from polymer_claims.attestation import build_certificate, certificate_dsse_envelope
    from polymer_claims.io import load_corpus
    cert = build_certificate(load_corpus(str(cp)), "c1", ledger=None, target_q=0.05)
    expected = certificate_dsse_envelope(cert).model_dump_json(by_alias=True, exclude_none=True) + "\n"
    assert cli_out == expected                       # byte-identical, unsigned


def test_export_attestation_dsse_unsigned_is_byte_identical(tmp_path):
    cp = _corpus_path(tmp_path)
    out_path = tmp_path / "att.ndjson"
    assert main(["export-attestation", str(cp), "--format", "dsse", "--out", str(out_path)]) == 0
    from polymer_claims.attestation import (
        build_attestation_statements, dsse_envelope, resolve_contract_index,
    )
    from polymer_claims.io import load_corpus
    corpus = load_corpus(str(cp))
    idx = resolve_contract_index(corpus)
    expected = "".join(
        dsse_envelope(s).model_dump_json(by_alias=True, exclude_none=True) + "\n"
        for s in build_attestation_statements(corpus, contract_index=idx)
    )
    assert out_path.read_text() == expected          # byte-identical, unsigned


def test_key_rejected_on_non_dsse_format(tmp_path, capsys):
    cp = _corpus_path(tmp_path)
    key, pub = tmp_path / "k.key", tmp_path / "k.pub"
    assert main(["keygen", "--key", str(key), "--pub-key", str(pub)]) == 0
    assert main(["certify", "c1", "--corpus", str(cp), "--format", "json", "--key", str(key)]) == 1
    assert main(["export-attestation", str(cp), "--format", "bundle", "--key", str(key)]) == 1


def test_malformed_private_key_is_rc1_not_traceback(tmp_path, capsys):
    cp = _corpus_path(tmp_path)
    bad = tmp_path / "bad.key"
    bad.write_text("-----BEGIN PRIVATE KEY-----\nnope\n-----END PRIVATE KEY-----\n")
    assert main(["certify", "c1", "--corpus", str(cp), "--format", "dsse", "--key", str(bad)]) == 1
    assert main(["export-attestation", str(cp), "--format", "dsse", "--key", str(bad)]) == 1
    # an unreadable (missing) key path is also rc 1, not a traceback
    missing = tmp_path / "nope.key"
    assert main(["certify", "c1", "--corpus", str(cp), "--format", "dsse", "--key", str(missing)]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_keygen_force_resets_private_key_to_0600(tmp_path):
    import os
    import stat
    key, pub = tmp_path / "k.key", tmp_path / "k.pub"
    key.write_text("stale")
    key.chmod(0o644)                                   # pre-existing world-readable file
    assert main(["keygen", "--key", str(key), "--pub-key", str(pub), "--force"]) == 0
    assert stat.S_IMODE(os.stat(key).st_mode) == 0o600  # overwrite must restore 0600


def test_certify_dsse_signed_then_verify(tmp_path, capsys):
    cp = _corpus_path(tmp_path)
    key, pub = tmp_path / "k.key", tmp_path / "k.pub"
    assert main(["keygen", "--key", str(key), "--pub-key", str(pub)]) == 0
    rc = main(["certify", "c1", "--corpus", str(cp), "--format", "dsse", "--key", str(key)])
    assert rc == 0
    out = capsys.readouterr().out
    env = json.loads(out)
    assert len(env["signatures"]) == 1 and env["signatures"][0]["sig"]
    signed_path = tmp_path / "cert.dsse.json"
    signed_path.write_text(out)
    assert main(["verify-dsse", str(signed_path), "--pub-key", str(pub)]) == 0


def test_export_attestation_dsse_signed(tmp_path):
    cp = _corpus_path(tmp_path)
    key, pub = tmp_path / "k.key", tmp_path / "k.pub"
    assert main(["keygen", "--key", str(key), "--pub-key", str(pub)]) == 0
    out_path = tmp_path / "att.ndjson"
    rc = main(["export-attestation", str(cp), "--format", "dsse", "--key", str(key), "--out", str(out_path)])
    assert rc == 0
    lines = [ln for ln in out_path.read_text().splitlines() if ln.strip()]
    assert lines and all(json.loads(ln)["signatures"] for ln in lines)
    assert main(["verify-dsse", str(out_path), "--pub-key", str(pub)]) == 0
