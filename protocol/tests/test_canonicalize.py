from polymer_grammar import Status, are_equivalent

from polymer_protocol.canonicalize import canonicalize
from polymer_protocol.corpus import Corpus
from tests.conftest import make_claim, make_plan


def test_structurally_identical_claims_become_one_equivalence_class(empty_ledger):
    plan = make_plan(0.01, 0.05)
    # a and b are structurally identical except for id (same pattern/leaf-less-key/plan).
    a = make_claim("a", status=Status.PENDING, plan=plan)
    b = make_claim("b", status=Status.PENDING, plan=plan)
    corpus = Corpus(claims=(a, b), fdr_ledger=empty_ledger)
    out = canonicalize(corpus)
    assert len(out.equivalences) == 1
    eq = out.equivalences[0]
    assert {eq.left, eq.right} == {"a", "b"}
    assert eq.status == Status.LICENSED
    # they are now in one equivalence class (back-compat LICENSED gating)
    assert are_equivalent("a", "b", out.equivalences)


def test_distinct_claims_are_not_collapsed(empty_ledger):
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    b = make_claim("b", status=Status.PENDING, plan=make_plan(0.99, 0.05))
    corpus = Corpus(claims=(a, b), fdr_ledger=empty_ledger)
    out = canonicalize(corpus)
    assert out.equivalences == ()


def test_three_way_bucket_all_in_one_class(empty_ledger):
    plan = make_plan(0.01, 0.05)
    a = make_claim("a", status=Status.PENDING, plan=plan)
    b = make_claim("b", status=Status.PENDING, plan=plan)
    c = make_claim("c", status=Status.PENDING, plan=plan)
    corpus = Corpus(claims=(a, b, c), fdr_ledger=empty_ledger)
    out = canonicalize(corpus)
    assert len(out.equivalences) == 2  # star: a->b, a->c
    assert are_equivalent("b", "c", out.equivalences)  # transitive via a


def test_canonicalize_is_idempotent(empty_ledger):
    plan = make_plan(0.01, 0.05)
    corpus = Corpus(
        claims=(make_claim("a", status=Status.PENDING, plan=plan),
                make_claim("b", status=Status.PENDING, plan=plan)),
        fdr_ledger=empty_ledger,
    )
    once = canonicalize(corpus)
    twice = canonicalize(once)
    assert once.equivalences == twice.equivalences
