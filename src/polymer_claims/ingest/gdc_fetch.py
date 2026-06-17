"""GDC open-access fetch by pinned UUID + MD5 fixity. Network I/O via urllib (stdlib).
The pinned UUIDs live in tcga_laml_manifest.json (committed); the data they fetch is gitignored."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

_GDC_DATA = "https://api.gdc.cancer.gov/data/"


def gdc_data_url(uuid: str) -> str:
    return f"{_GDC_DATA}{uuid}"


def verify_md5(data: bytes, expected_hex: str) -> None:
    got = hashlib.md5(data).hexdigest()
    if got != expected_hex:
        raise ValueError(f"MD5 mismatch: got {got}, expected {expected_hex}")


def load_pinned_manifest() -> dict:
    """The committed pinned-UUID recipe shipped alongside this module."""
    return json.loads((Path(__file__).parent / "tcga_laml_manifest.json").read_text())


def fetch_file(uuid: str, md5: str, dest: Path) -> bytes:
    """Download one GDC file by UUID, verify MD5, cache to dest (skip re-download if cached+valid)."""
    if dest.is_file():
        cached = dest.read_bytes()
        if hashlib.md5(cached).hexdigest() == md5:
            return cached
    with urllib.request.urlopen(gdc_data_url(uuid)) as resp:  # noqa: S310 — fixed GDC https host
        data = resp.read()
    verify_md5(data, md5)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return data
