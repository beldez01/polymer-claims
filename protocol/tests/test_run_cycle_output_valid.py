"""Integrity guard (audit #4): run_cycle threads frozen models via model_copy(update=...),
which BYPASSES Pydantic validation. This asserts the resulting Corpus always RE-VALIDATES
(model_copy never produced an invalid (status, pending_reason, licensing) combination or broke a
corpus-level invariant), across the licensing / rejection / generation paths."""
from __future__ import annotations

from polymer_grammar import Direction, Proposition, Status

from polymer_protocol import Corpus, run_cycle
from polymer_protocol.proposers import rival_generation
from tests.conftest import make_claim, make_plan


def _assert_revalidates(corpus: Corpus) -> None:
    # A full re-validate from the serialized form must reproduce the corpus exactly — any invalid
    # field combo a stage's model_copy could have minted would raise here instead.
    assert Corpus.model_validate(corpus.model_dump()) == corpus
    assert Corpus.model_validate_json(corpus.model_dump_json()) == corpus


def test_licensing_cycle_output_revalidates(empty_ledger, adapters, ctx):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    res = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert res.corpus.by_id()["a"].status == Status.LICENSED
    _assert_revalidates(res.corpus)


def test_rejection_cycle_output_revalidates(empty_ledger, adapters, ctx):
    # value 0.99 fails the < 0.05 criterion -> refuted -> REJECTED
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.99, 0.05))
    res = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    _assert_revalidates(res.corpus)


def test_generation_cycle_output_revalidates(empty_ledger, adapters, ctx):
    # a POSITIVE planless source drives rival_generation to admit new conjectured nodes
    src = make_claim("SRC", status=Status.CONJECTURED)
    src = src.model_copy(update={
        "conclusion": Proposition(direction=Direction.POSITIVE, estimand="beta", descriptor="x"),
    })
    res = run_cycle(
        Corpus(claims=(src,), fdr_ledger=empty_ledger),
        adapters, ctx, proposers=(rival_generation,),
    )
    _assert_revalidates(res.corpus)
