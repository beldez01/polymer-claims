import hashlib
import pytest
from polymer_claims.ingest._pinned import resolve_pinned_file, PinnedInputError

def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def test_local_dir_resolves_and_verifies(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "x.bin").write_bytes(b"hello")
    out = resolve_pinned_file("x.bin", local=src, url=None, sha256=_sha(b"hello"),
                              cache_dir=tmp_path / "cache", allow_fetch=False)
    assert out.read_bytes() == b"hello"

def test_local_file_path_used_directly(tmp_path):
    f = tmp_path / "matrix.tsv.gz"
    f.write_bytes(b"data")
    out = resolve_pinned_file("matrix.tsv.gz", local=f, url=None, sha256=_sha(b"data"),
                              cache_dir=tmp_path / "cache", allow_fetch=False)
    assert out == f

def test_cache_hit(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "y.bin").write_bytes(b"world")
    out = resolve_pinned_file("y.bin", local=None, url=None, sha256=_sha(b"world"),
                              cache_dir=cache, allow_fetch=False)
    assert out == cache / "y.bin"

def test_sha_mismatch_raises(tmp_path):
    src = tmp_path / "s"
    src.mkdir()
    (src / "z.bin").write_bytes(b"abc")
    with pytest.raises(PinnedInputError, match="sha256 mismatch"):
        resolve_pinned_file("z.bin", local=src, url=None, sha256=_sha(b"different"),
                            cache_dir=tmp_path / "c", allow_fetch=False)

def test_absent_without_fetch_is_actionable(tmp_path):
    with pytest.raises(PinnedInputError, match="--fetch"):
        resolve_pinned_file("missing.bin", local=None, url="https://example/missing.bin",
                            sha256=_sha(b""), cache_dir=tmp_path / "c", allow_fetch=False)

def test_lfs_pointer_detected(tmp_path):
    src = tmp_path / "s"
    src.mkdir()
    (src / "p.bin").write_bytes(b"version https://git-lfs.github.com/spec/v1\n")
    with pytest.raises(PinnedInputError, match="pointer"):
        resolve_pinned_file("p.bin", local=src, url=None, sha256="deadbeef",
                            cache_dir=tmp_path / "c", allow_fetch=False)
