import json

from polymer_claims.cli import main


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
