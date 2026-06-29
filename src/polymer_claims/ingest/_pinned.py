"""Resolve a pinned external input (local file/dir -> cache -> opt-in fetch) and verify its SHA-256.
Used by the real-data kernel parity gate for the Xena matrix and the cBioPortal inputs. Fetch is
opt-in (network only when allow_fetch=True)."""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

_LFS_POINTER = b"version https://git-lfs"
_HTML_SNIFF = (b"<!doctype html", b"<html")


class PinnedInputError(RuntimeError):
    """A pinned input could not be resolved or failed verification."""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _looks_like_pointer(path: Path) -> bool:
    with open(path, "rb") as fh:
        head = fh.read(64).lstrip().lower()
    return head.startswith(_LFS_POINTER) or any(head.startswith(s) for s in _HTML_SNIFF)


def _verify(path: Path, sha256: str, filename: str, *, cleanup_on_fail: bool = False) -> Path:
    if _looks_like_pointer(path):
        if cleanup_on_fail:
            path.unlink(missing_ok=True)
        raise PinnedInputError(
            f"{filename}: got a git-LFS pointer or HTML page, not the data blob — fetch the raw file.")
    got = _sha256(path)
    if got != sha256:
        if cleanup_on_fail:
            path.unlink(missing_ok=True)
        raise PinnedInputError(f"{filename}: sha256 mismatch (expected {sha256}, got {got}).")
    return path


def resolve_pinned_file(
    filename: str, *, local: Path | None, url: str | None, sha256: str,
    cache_dir: Path, allow_fetch: bool,
) -> Path:
    """Return a path to `filename` whose SHA-256 == `sha256`.

    Resolution order: `local` (a file, or a dir containing `filename`) -> `cache_dir/filename`
    -> (only if allow_fetch and url) download `url` into cache atomically. Verifies SHA-256 on the
    resolved path; raises PinnedInputError on mismatch, pointer/HTML bytes, or an unresolvable input.
    """
    if local is not None:
        candidate = local if local.is_file() else local / filename
        if candidate.is_file():
            return _verify(candidate, sha256, filename)

    cached = cache_dir / filename
    if cached.is_file():
        return _verify(cached, sha256, filename)

    if not (allow_fetch and url):
        suffix = (
            f"or pass --fetch to download from {url!r}."
            if url
            else "(no download URL is pinned for this input)."
        )
        raise PinnedInputError(
            f"{filename}: not found locally or in cache ({cache_dir}). Supply it via "
            f"--xena/--cbioportal, {suffix}")

    cache_dir.mkdir(parents=True, exist_ok=True)
    # unique temp name so concurrent runs don't trample each other (spec §3: atomic .part-<n>)
    fd, tmp_name = tempfile.mkstemp(prefix=f"{filename}.part-", dir=cache_dir)
    os.close(fd)
    tmp = Path(tmp_name)
    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as out:  # noqa: S310 (pinned + sha-verified)
        shutil.copyfileobj(resp, out)
    _verify(tmp, sha256, filename, cleanup_on_fail=True)
    os.replace(tmp, cached)  # atomic: only a verified file lands at the final name
    return cached
