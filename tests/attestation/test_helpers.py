from __future__ import annotations

from polymer_claims._hashing import canonical_sha256
from polymer_claims.attestation import _bare_hex, _digest_or_none, _subject

from tests.attestation._fixtures import licensed_claim, licensing, mc, sat


def test_bare_hex_strips_algorithm_prefix():
    assert _bare_hex("sha256:abc123") == "abc123"
    assert _bare_hex("abc123") == "abc123"


def test_digest_or_none_accepts_valid_sha256_and_rejects_others():
    valid = "sha256:" + "a" * 64
    assert _digest_or_none(valid).sha256 == "a" * 64
    assert _digest_or_none("h1") is None
    assert _digest_or_none(None) is None
    assert _digest_or_none("sha256:tooshort") is None


def test_subject_digest_matches_canonical_claim_hash():
    claim = licensed_claim("c1", licensing(sat(mc())))
    expected = canonical_sha256(claim.model_dump(mode="json")).split(":", 1)[1]
    subj = _subject(claim)
    assert subj.name == "c1"
    assert subj.digest.sha256 == expected
