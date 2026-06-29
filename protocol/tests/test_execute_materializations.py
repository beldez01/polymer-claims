from polymer_grammar import MaterializationContext, Status

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus
from polymer_protocol.execute import execute_ground
from tests.conftest import make_claim, make_plan


def _executable(cid, empty_ledger):
    # value 0.01 < threshold 0.05 -> SATISFIED by the reference adapters (Comparator.LT default)
    c = make_claim(cid, status=Status.PENDING, plan=make_plan(0.01, 0.05))
    return c, empty_ledger


def test_per_claim_materialization_is_stamped_on_satisfaction(empty_ledger, adapters):
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(a, b), fdr_ledger=empty_ledger))
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    mats = {
        "a": MaterializationContext(id="M", api_version="v1", data_version="d1",
                                    dimnames_hash="sha256:aaa", profile_hash="sha256:pa"),
        "b": MaterializationContext(id="M", api_version="v1", data_version="d1",
                                    dimnames_hash="sha256:bbb", profile_hash="sha256:pb"),
    }
    _, records, _ = execute_ground(corpus, adapters, base, materializations=mats)
    by_id = {r.claim_id: r for r in records}
    assert by_id["a"].evaluation.satisfaction.materialization.dimnames_hash == "sha256:aaa"
    assert by_id["b"].evaluation.satisfaction.materialization.dimnames_hash == "sha256:bbb"
    assert by_id["a"].evaluation.satisfaction.materialization.profile_hash == "sha256:pa"


def test_no_map_uses_base_ctx_unchanged(empty_ledger, adapters):
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(a,), fdr_ledger=empty_ledger))
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    _, records, _ = execute_ground(corpus, adapters, base)
    m = records[0].evaluation.satisfaction.materialization
    assert m.data_version == "d1" and m.dimnames_hash is None


def test_claim_absent_from_map_falls_back_to_base(empty_ledger, adapters):
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(a, b), fdr_ledger=empty_ledger))
    base = MaterializationContext(id="M", api_version="v1", data_version="d1")
    mats = {"a": MaterializationContext(id="M", api_version="v1", data_version="d1",
                                        dimnames_hash="sha256:aaa")}
    _, records, _ = execute_ground(corpus, adapters, base, materializations=mats)
    by_id = {r.claim_id: r for r in records}
    assert by_id["a"].evaluation.satisfaction.materialization.dimnames_hash == "sha256:aaa"
    assert by_id["b"].evaluation.satisfaction.materialization.dimnames_hash is None
