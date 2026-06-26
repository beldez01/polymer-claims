import base64
import hashlib

import pytest

from polymer_claims import transparency as T
from polymer_claims.attestation import DsseEnvelope, DsseSignature


def _lh(d: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + d).digest()


def _nh(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def test_leaf_and_node_hash_are_domain_separated():
    assert T.leaf_hash(b"abc") == hashlib.sha256(b"\x00abc").digest()
    assert T.node_hash(b"L" * 32, b"R" * 32) == hashlib.sha256(b"\x01" + b"L" * 32 + b"R" * 32).digest()


def test_merkle_root_n1_is_leaf_hash():
    assert T.merkle_root([b"d0"]) == _lh(b"d0")


def test_merkle_root_n2():
    assert T.merkle_root([b"d0", b"d1"]) == _nh(_lh(b"d0"), _lh(b"d1"))


def test_merkle_root_n3_splits_at_largest_power_of_two_below_n():
    # k = 2 -> left = {d0,d1}, right = {d2}
    leaves = [b"d0", b"d1", b"d2"]
    expected = _nh(_nh(_lh(b"d0"), _lh(b"d1")), _lh(b"d2"))
    assert T.merkle_root(leaves) == expected


def test_merkle_root_n5_split_structure():
    # k = 4 -> left = {d0..d3}, right = {d4}
    d = [bytes([i]) for i in range(5)]
    lh = [_lh(x) for x in d]
    left = _nh(_nh(lh[0], lh[1]), _nh(lh[2], lh[3]))
    expected = _nh(left, lh[4])
    assert T.merkle_root(d) == expected


def test_merkle_root_empty_raises():
    with pytest.raises(ValueError):
        T.merkle_root([])


@pytest.mark.parametrize("n", list(range(1, 10)))
def test_inclusion_proof_round_trip_every_leaf(n):
    leaves = [bytes([i]) for i in range(n)]
    root = T.merkle_root(leaves)
    for idx in range(n):
        proof = T.inclusion_proof(leaves, idx)
        assert T.verify_inclusion(T.leaf_hash(leaves[idx]), idx, n, proof, root) is True


def test_verify_inclusion_rejects_tampered_proof():
    leaves = [bytes([i]) for i in range(6)]
    root = T.merkle_root(leaves)
    proof = T.inclusion_proof(leaves, 2)
    bad = list(proof)
    bad[0] = bytes(32)  # flip a sibling
    assert T.verify_inclusion(T.leaf_hash(leaves[2]), 2, 6, bad, root) is False


def test_verify_inclusion_rejects_wrong_index_size_root_and_malformed():
    leaves = [bytes([i]) for i in range(6)]
    root = T.merkle_root(leaves)
    proof = T.inclusion_proof(leaves, 2)
    leaf = T.leaf_hash(leaves[2])
    assert T.verify_inclusion(leaf, 3, 6, proof, root) is False          # wrong index
    # A 6-leaf proof (length 3) is structurally inconsistent with a much larger tree -> rejected.
    # (Adjacent sizes like 7 can ALIAS for some indices — same audit path — so size alone is not the
    # guarantee; root binding is, since (tree_size, root) are signed together in the checkpoint.)
    assert T.verify_inclusion(leaf, 2, 100, proof, root) is False        # wrong tree_size (length mismatch)
    assert T.verify_inclusion(leaf, 2, 6, proof, bytes(32)) is False     # wrong root
    assert T.verify_inclusion(leaf, 2, 6, proof + [bytes(32)], root) is False  # over-long
    assert T.verify_inclusion(leaf, 2, 6, [], root) is False             # truncated
    assert T.verify_inclusion(leaf, -1, 6, proof, root) is False         # bad index, no raise


def test_canonical_entry_bytes_is_sorted_compact_json_of_signed_envelope():
    env = DsseEnvelope(
        payload_type="application/vnd.polymer.certificate+json",
        payload=base64.b64encode(b"hello").decode("ascii"),
        signatures=(DsseSignature(sig="QUJD", keyid="abcd1234"),),
    )
    out = T.canonical_entry_bytes(env)
    import json
    parsed = json.loads(out)
    assert parsed == {
        "payloadType": "application/vnd.polymer.certificate+json",
        "payload": base64.b64encode(b"hello").decode("ascii"),
        "signatures": [{"sig": "QUJD", "keyid": "abcd1234"}],
    }
    assert out == json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert T.canonical_entry_bytes(env) == out  # deterministic
