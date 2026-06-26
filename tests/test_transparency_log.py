import pytest

from polymer_claims import signing
from polymer_claims import transparency as T

pytest.importorskip("cryptography")


def _fixed_clock():
    return "2026-06-25T00:00:00Z"


def test_submit_assigns_sequential_indices_and_verifiable_entries(tmp_path):
    priv, pub = signing.generate_keypair()
    log = T.LocalInclusionLog(tmp_path, priv, clock=_fixed_clock)
    entries = [log.submit(f"entry-{i}".encode()) for i in range(3)]
    assert [e.log_index for e in entries] == [0, 1, 2]
    for i, e in enumerate(entries):
        assert e.kind_version == T.LOCAL_KIND_VERSION
        assert e.integrated_time is None
        assert e.log_id == signing.keyid_for(pub)
        fields = T.parse_checkpoint(e.checkpoint)
        assert fields.tree_size == i + 1
        # inclusion proof for THIS entry verifies against the checkpoint root at submit time
        leaf = T.leaf_hash(f"entry-{i}".encode())
        proof = [bytes.fromhex(h) for h in e.inclusion_proof]
        assert T.verify_inclusion(leaf, i, i + 1, proof, fields.root_hash) is True
        assert T.verify_checkpoint(e.checkpoint, pub) is True


def test_reopening_continues_indices_and_grows_root(tmp_path):
    priv, _ = signing.generate_keypair()
    log1 = T.LocalInclusionLog(tmp_path, priv, clock=_fixed_clock)
    log1.submit(b"a")
    log1.submit(b"b")
    log2 = T.LocalInclusionLog(tmp_path, priv, clock=_fixed_clock)
    e = log2.submit(b"c")
    assert e.log_index == 2
    assert T.parse_checkpoint(e.checkpoint).tree_size == 3


def test_public_key_pem_matches_the_log_key(tmp_path):
    priv, pub = signing.generate_keypair()
    log = T.LocalInclusionLog(tmp_path, priv, clock=_fixed_clock)
    assert log.public_key_pem == signing.serialize_public_pem(pub)


def test_determinism_fixed_key_and_clock(tmp_path):
    priv, _ = signing.generate_keypair()
    a = T.LocalInclusionLog(tmp_path / "a", priv, clock=_fixed_clock).submit(b"x")
    b = T.LocalInclusionLog(tmp_path / "b", priv, clock=_fixed_clock).submit(b"x")
    assert a.checkpoint == b.checkpoint and a.inclusion_proof == b.inclusion_proof
