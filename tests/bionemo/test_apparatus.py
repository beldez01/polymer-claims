from polymer_claims.bionemo.apparatus import BioNeMoApparatus, build_materialization_context


def _app():
    return BioNeMoApparatus(
        endpoint="https://x/fold", model_id="openfold", model_version="2.1",
        payload_schema=("sequence",),
    )


def test_content_hash_is_deterministic_and_prefixed():
    h1 = _app().content_hash()
    h2 = _app().content_hash()
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_context_carries_apparatus_provenance():
    ctx = build_materialization_context(_app(), id="M1", api_version="v1", data_version="d1")
    assert ctx.semantic_run_id == _app().content_hash()
    assert ctx.profile_hash == _app().content_hash()
    assert "nim:openfold@2.1" in ctx.shared_cause_factors
