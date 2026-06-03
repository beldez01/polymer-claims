from polymer_grammar import Status

from polymer_protocol.corpus import Corpus
from polymer_protocol.cycle import run_cycle
from tests.conftest import make_claim, make_plan


def test_cycle_licenses_a_satisfied_claim(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    result = run_cycle(Corpus(claims=(c,), fdr_ledger=empty_ledger), adapters, ctx)
    assert result.corpus.by_id()["a"].status == Status.LICENSED
    assert result.corpus.fdr_ledger.n_tests == 1
    assert result.gated_lane == ()
    # audit records one line per stage
    assert {a.stage for a in result.audit} == {
        "represent", "canonicalize", "safety_gate", "commit",
        "execute_ground", "verify_stage", "integrate",
    }


def test_cycle_reports_gated_lane(empty_ledger, ctx, adapters):
    from polymer_grammar import Governance, HazardClass

    hot = make_claim(
        "h", status=Status.PENDING, plan=make_plan(0.01, 0.05),
        governance=Governance(hazard_class=HazardClass.HIGH),
    )
    result = run_cycle(Corpus(claims=(hot,), fdr_ledger=empty_ledger), adapters, ctx)
    assert result.gated_lane == ("h",)
    # gated claim was NOT executed -> still PENDING, no FDR test
    assert result.corpus.by_id()["h"].status == Status.PENDING
    assert result.corpus.fdr_ledger.n_tests == 0
