from __future__ import annotations

import hashlib

import pytest

from polymer_claims.ingest.gdc_fetch import gdc_data_url, verify_md5


def test_gdc_data_url():
    assert gdc_data_url("abc-123") == "https://api.gdc.cancer.gov/data/abc-123"


def test_verify_md5_passes_and_fails():
    data = b"hello"
    verify_md5(data, hashlib.md5(data).hexdigest())  # no raise
    with pytest.raises(ValueError):
        verify_md5(data, "deadbeef")
