from polymer_claims.bionemo.client import NimClient, NimRequest, NimResponse


def _canned(req, api_key):
    assert api_key == "k"
    return NimResponse(status=200, body={"score": 0.12, "model": "openfold-2.1"}, model_version=None)


def test_call_returns_response_and_extracts_model_version(tmp_path):
    client = NimClient(transport=_canned, cache_dir=tmp_path, api_key="k")
    resp = client.call(NimRequest(endpoint="https://x/fold", payload={"seq": "MA"}))
    assert resp.body["score"] == 0.12
    assert resp.model_version == "openfold-2.1"


def test_second_identical_call_hits_cache_not_transport(tmp_path):
    calls = {"n": 0}

    def counting(req, api_key):
        calls["n"] += 1
        return NimResponse(status=200, body={"score": 0.12, "model": "m1"}, model_version=None)

    client = NimClient(transport=counting, cache_dir=tmp_path, api_key="k")
    req = NimRequest(endpoint="https://x/fold", payload={"seq": "MA"})
    a = client.call(req)
    b = client.call(req)
    assert calls["n"] == 1            # transport hit once; second served from cache
    assert a.body == b.body
