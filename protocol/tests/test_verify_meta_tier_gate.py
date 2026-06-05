from __future__ import annotations

from polymer_grammar import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    PatternRef,
    PatternTarget,
    RepresentationRevision,
    RivalSetClosure,
    RevisionOperation,
    Satisfaction,
    SatisfactionVerdict,
    Status,
    meets_meta_tier_bar,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.cycle import run_cycle
from tests.conftest import make_claim, make_plan


def _revision():
    return RepresentationRevision(
        operation=RevisionOperation.DEPRECATE,
        target=PatternTarget(patterns=(PatternRef(id="adjusted_effect", version="v1"),)),
        rationale="contested representation",
    )


def test_planned_representation_revision_is_not_auto_licensed(empty_ledger, ctx, adapters):
    # a revision claim that would otherwise license (satisfied, in-extension, clears the bar) is HELD
    # PENDING — the auto SEVERE_TEST/OPEN licensing fails meets_meta_tier_bar.
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05),
                   representation_revision=_revision())
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    out = result.corpus.by_id()["a"]
    assert out.status == Status.PENDING
    assert out.licensing is None


def test_non_revision_claim_in_same_position_licenses(empty_ledger, ctx, adapters):
    # the gate is revision-specific: an otherwise-identical plain claim DOES license.
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert result.corpus.by_id()["a"].status == Status.LICENSED


def test_meta_tier_bar_truth_in_gate_context():
    # the auto-assembled licensing fails the bar (why the gate fires); replication-grade passes.
    mat = MaterializationContext(id="m1", api_version="v1", data_version="v1")
    sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=mat)
    severe = Licensing(route=LicenseRoute.SEVERE_TEST, rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
                       satisfactions=(sat,))
    assert meets_meta_tier_bar(severe) is False
    mat2 = MaterializationContext(id="m2", api_version="v1", data_version="v1")
    sat2 = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=mat2)
    repl = Licensing(route=LicenseRoute.REPLICATION, rival_set_closure=RivalSetClosure.ENUMERATED,
                     rivals_considered=("r1",), satisfactions=(sat, sat2))
    assert meets_meta_tier_bar(repl) is True
