from __future__ import annotations

from polymer_claims._hashing import canonical_sha256


def test_canonical_sha256_is_deterministic_and_prefixed():
    h1 = canonical_sha256({"b": 2, "a": 1})
    h2 = canonical_sha256({"a": 1, "b": 2})  # key order must not matter
    assert h1 == h2
    assert h1.startswith("sha256:")
    assert len(h1) == len("sha256:") + 64  # hex digest


def test_canonical_sha256_is_content_sensitive():
    assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 2})


def test_canonical_sha256_matches_inline_recipe():
    import hashlib
    import json
    obj = {"feature_ids": ["cg1", "cg2"], "sample_ids": ["S1"]}
    expected = "sha256:" + hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert canonical_sha256(obj) == expected
