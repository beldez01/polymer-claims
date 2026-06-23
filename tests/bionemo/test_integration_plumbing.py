from polymer_grammar import Status
from examples.bionemo_plumbing.run import run_plumbing


def test_cached_nim_run_licenses_the_claim(tmp_path):
    result = run_plumbing(cache_dir=tmp_path)
    claim = result.corpus.by_id()["bionemo-plumbing-1"]
    assert claim.status == Status.LICENSED
