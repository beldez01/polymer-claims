from polymer_grammar import Status

from polymer_protocol.corpus import Corpus, CycleScaffolding
from polymer_protocol.integrate import integrate
from tests.conftest import make_claim, make_plan


def _exec_record_with_value(claim_id, value, ctx, adapters, empty_ledger):
    """Helper: produce a real ExecRecord by executing a const-`value` plan."""
    from polymer_protocol.commit import commit
    from polymer_protocol.execute import execute_ground

    c = make_claim(claim_id, status=Status.PENDING, plan=make_plan(value, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    _out, records = execute_ground(corpus, adapters, ctx)
    return records[0]


def test_fdr_ledger_advances_one_test_per_executed_claim(empty_ledger, ctx, adapters):
    rec = _exec_record_with_value("a", 0.01, ctx, adapters, empty_ledger)
    licensed = make_claim("a", status=Status.LICENSED)  # post-VERIFY status
    corpus = Corpus(claims=(licensed,), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out, skipped = integrate(corpus, scaffolding, (rec,))
    assert out.fdr_ledger.n_tests == 1
    assert out.fdr_ledger.tests[0].claim_id == "a"
    assert out.fdr_ledger.tests[0].e_value == 0.01
    assert skipped == ()


def test_non_pvalue_terminal_is_skipped(empty_ledger, ctx, adapters):
    # terminal value 7.0 is outside [0,1] -> not a valid p-value -> skipped, logged.
    rec = _exec_record_with_value("a", 7.0, ctx, adapters, empty_ledger)
    c = make_claim("a", status=Status.PENDING)
    corpus = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out, skipped = integrate(corpus, scaffolding, (rec,))
    assert out.fdr_ledger.n_tests == 0
    assert skipped == ("a",)


def test_integrate_keeps_consistent_claims(empty_ledger, ctx, adapters):
    rec = _exec_record_with_value("a", 0.01, ctx, adapters, empty_ledger)
    corpus = Corpus(claims=(make_claim("a", status=Status.LICENSED),), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out, _skipped = integrate(corpus, scaffolding, (rec,))
    assert "a" in out.by_id()  # no inconsistency -> claim survives


def test_fdr_ledger_order_is_stable_with_two_claims(empty_ledger, ctx, adapters):
    rec_a = _exec_record_with_value("a", 0.01, ctx, adapters, empty_ledger)
    rec_b = _exec_record_with_value("b", 0.03, ctx, adapters, empty_ledger)
    corpus = Corpus(
        claims=(make_claim("a", status=Status.LICENSED), make_claim("b", status=Status.LICENSED)),
        fdr_ledger=empty_ledger,
    )
    scaffolding = CycleScaffolding(grounded_extension=("a", "b"))
    out_fwd, _ = integrate(corpus, scaffolding, (rec_a, rec_b))
    out_rev, _ = integrate(corpus, scaffolding, (rec_b, rec_a))
    assert out_fwd.fdr_ledger == out_rev.fdr_ledger  # integrate sorts -> order-independent
    assert out_fwd.fdr_ledger.tests[0].claim_id == "a"  # "a" < "b" lexicographically
    assert out_fwd.fdr_ledger.tests[1].claim_id == "b"


def test_string_terminal_is_skipped(empty_ledger):
    from polymer_grammar import (
        EvaluationResult, ExecValue, SatisfactionVerdict, VerifiedEvaluation,
    )
    from polymer_protocol.corpus import ExecRecord

    string_result = EvaluationResult(
        verdict=SatisfactionVerdict.UNDETERMINED, terminal=ExecValue(value="high"),
        nodes=(), adapter_identity="identity", status="complete",
    )
    ev = VerifiedEvaluation(results=(string_result,), agreement=False)
    rec = ExecRecord(claim_id="z", evaluation=ev)
    corpus = Corpus(claims=(make_claim("z", status=Status.PENDING),), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("z",))
    out, skipped = integrate(corpus, scaffolding, (rec,))
    assert out.fdr_ledger.n_tests == 0
    assert skipped == ("z",)
