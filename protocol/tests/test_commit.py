from polymer_grammar import GenerationMode, Provenance, Status

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus
from tests.conftest import make_claim, make_plan


def test_commit_locks_pending_claim_without_provenance(empty_ledger):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    out = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    locked = out.by_id()["a"]
    assert locked.provenance is not None
    assert locked.provenance.generated_by == GenerationMode.IMPORTED
    assert locked.provenance.search_cardinality == 1
    assert locked.provenance.preregistration_hash is not None


def test_commit_preserves_existing_provenance(empty_ledger):
    prov = Provenance(generated_by=GenerationMode.HUMAN_AUTHORED, search_cardinality=7)
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05), provenance=prov)
    out = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    locked = out.by_id()["a"]
    assert locked.provenance.generated_by == GenerationMode.HUMAN_AUTHORED
    assert locked.provenance.search_cardinality == 7  # untouched
    assert locked.provenance.preregistration_hash is not None


def test_commit_is_idempotent_and_does_not_overwrite_lock(empty_ledger):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    once = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    twice = commit(once)
    assert (
        once.by_id()["a"].provenance.preregistration_hash
        == twice.by_id()["a"].provenance.preregistration_hash
    )
    # second pass changes nothing
    assert once.by_id()["a"] == twice.by_id()["a"]


def test_commit_skips_claims_without_a_plan(empty_ledger):
    c = make_claim("a", status=Status.PENDING)  # no evaluation_plan
    out = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    assert out.by_id()["a"].provenance is None


def test_commit_does_not_overwrite_lock_when_plan_changes(empty_ledger):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    once = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    original_lock = once.by_id()["a"].provenance.preregistration_hash
    # simulate post-hoc plan replacement (what VERIFY/anti-HARKing must later detect)
    mutated = once.by_id()["a"].model_copy(update={"evaluation_plan": make_plan(0.99, 0.05)})
    twice = commit(Corpus(claims=(mutated,), fdr_ledger=empty_ledger))
    assert twice.by_id()["a"].provenance.preregistration_hash == original_lock


def test_commit_skips_non_pending_claim_with_plan(empty_ledger):
    c = make_claim("a", status=Status.CONJECTURED, plan=make_plan(0.01, 0.05))
    out = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    assert out.by_id()["a"].provenance is None
