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
