import os
import pytest

LIVE = os.environ.get("POLYMER_BIONEMO_LIVE") == "1"
pytestmark = pytest.mark.skipif(not LIVE, reason="set POLYMER_BIONEMO_LIVE=1 + a real key to run")


def test_live_nim_returns_numeric(tmp_path):
    from polymer_claims.bionemo.auth import load_nvidia_api_key
    from polymer_claims.bionemo.client import NimClient, NimRequest, urllib_transport

    endpoint = os.environ["POLYMER_BIONEMO_ENDPOINT"]   # operator supplies the NIM URL
    client = NimClient(
        transport=urllib_transport, cache_dir=tmp_path, api_key=load_nvidia_api_key()
    )
    resp = client.call(NimRequest(endpoint=endpoint, payload={"sequence": "MAAAAA"}))
    assert resp.status == 200
    assert isinstance(resp.body, dict)
