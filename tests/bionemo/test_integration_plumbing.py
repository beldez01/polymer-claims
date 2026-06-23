from polymer_grammar import Status
from examples.bionemo_plumbing.run import run_plumbing


def test_cached_nim_run_licenses_the_claim(tmp_path):
    result = run_plumbing(cache_dir=tmp_path)
    claim = result.corpus.by_id()["bionemo-plumbing-1"]
    assert claim.status == Status.LICENSED


def test_licensed_claim_can_be_certified(tmp_path):
    from examples.bionemo_plumbing.run import certify_plumbing
    cert = certify_plumbing(cache_dir=tmp_path)
    assert cert.statement is not None
    assert any(sub.name == "bionemo-plumbing-1" for sub in cert.statement.subject)


def test_oracle_bound_claim_still_licenses_and_resolves(tmp_path):
    from polymer_grammar import Status, ValidationTier
    from polymer_claims.bionemo.oracle import bionemo_oracle_registry
    from examples.bionemo_plumbing.run import run_plumbing

    result = run_plumbing(cache_dir=tmp_path, with_oracle=True)
    claim = result.corpus.by_id()["bionemo-plumbing-1"]
    assert claim.status == Status.LICENSED

    reg = bionemo_oracle_registry(oracle_id="bionemo-plumbing@v1")
    assert reg.resolve("bionemo-plumbing@v1").validation_tier == ValidationTier.INDIRECT
