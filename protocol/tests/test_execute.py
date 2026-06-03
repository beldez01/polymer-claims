import pytest
from polymer_grammar import Governance, HazardClass, SelfLicensingError, Status

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus
from polymer_protocol.execute import execute_ground
from tests.conftest import make_claim, make_plan


def test_executes_committed_pending_claim(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    _out, records = execute_ground(corpus, adapters, ctx)
    assert _out is corpus
    assert len(records) == 1
    rec = records[0]
    assert rec.claim_id == "a"
    # value 0.01 < threshold 0.05, two distinct adapters agree -> Satisfaction minted
    assert rec.evaluation.satisfaction is not None


def test_skips_uncommitted_claim(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))  # NOT committed
    corpus = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    _out, records = execute_ground(corpus, adapters, ctx)
    assert records == ()


def test_skips_safety_gated_claim(empty_ledger, ctx, adapters):
    c = make_claim(
        "a", status=Status.PENDING, plan=make_plan(0.01, 0.05),
        governance=Governance(hazard_class=HazardClass.HIGH),
    )
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    _out, records = execute_ground(corpus, adapters, ctx)
    assert records == ()


def test_refuted_plan_mints_no_satisfaction(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.99, 0.05))  # 0.99 < 0.05 is false
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    _out, records = execute_ground(corpus, adapters, ctx)
    assert records[0].evaluation.satisfaction is None
    assert records[0].evaluation.agreement is True   # agreed REFUTED, not a disagreement
    assert records[0].evaluation.disagreement is None


def test_single_adapter_raises_self_licensing(empty_ledger, ctx):
    from polymer_grammar import IdentityAdapter

    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    with pytest.raises(SelfLicensingError):
        execute_ground(corpus, (IdentityAdapter(),), ctx)


def test_only_executable_subset_yields_records(empty_ledger, ctx, adapters):
    ok = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    gated = make_claim(
        "g", status=Status.PENDING, plan=make_plan(0.01, 0.05),
        governance=Governance(hazard_class=HazardClass.HIGH),
    )
    conj = make_claim("c")  # CONJECTURED, no plan
    corpus = commit(Corpus(claims=(ok, gated, conj), fdr_ledger=empty_ledger))
    _out, records = execute_ground(corpus, adapters, ctx)
    assert tuple(r.claim_id for r in records) == ("a",)


def test_adapter_disagreement_still_produces_a_record(empty_ledger, ctx):
    from polymer_grammar import IdentityAdapter, ReferenceAdapter
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    disagreeing = (IdentityAdapter(), ReferenceAdapter(identity="reference", perturb=10.0))
    _out, records = execute_ground(corpus, disagreeing, ctx)
    assert len(records) == 1
    assert records[0].evaluation.agreement is False
    assert records[0].evaluation.satisfaction is None
