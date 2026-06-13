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


def test_integrate_does_not_advance_fdr_ledger(empty_ledger, ctx, adapters):
    # Phase 2.1: FDR ledger now advances in VERIFY, not INTEGRATE. integrate() must leave
    # n_tests unchanged regardless of exec_records supplied.
    rec = _exec_record_with_value("a", 0.01, ctx, adapters, empty_ledger)
    licensed = make_claim("a", status=Status.LICENSED)  # post-VERIFY status
    corpus = Corpus(claims=(licensed,), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    before = corpus.fdr_ledger.n_tests
    out, skipped = integrate(corpus, scaffolding, (rec,))
    assert out.fdr_ledger.n_tests == before  # ledger unchanged by integrate
    assert skipped == ()                      # always empty tuple now


def test_integrate_returns_empty_skipped(empty_ledger, ctx, adapters):
    # integrate() always returns an empty skipped tuple (no FDR logic, no skipping).
    rec = _exec_record_with_value("a", 7.0, ctx, adapters, empty_ledger)
    c = make_claim("a", status=Status.PENDING)
    corpus = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out, skipped = integrate(corpus, scaffolding, (rec,))
    assert skipped == ()


def test_integrate_keeps_consistent_claims(empty_ledger, ctx, adapters):
    rec = _exec_record_with_value("a", 0.01, ctx, adapters, empty_ledger)
    corpus = Corpus(claims=(make_claim("a", status=Status.LICENSED),), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out, _skipped = integrate(corpus, scaffolding, (rec,))
    assert "a" in out.by_id()  # no inconsistency -> claim survives


def test_integrate_ledger_stable_with_two_claims(empty_ledger, ctx, adapters):
    # The ledger is untouched regardless of exec_record order (no FDR sorting logic).
    rec_a = _exec_record_with_value("a", 0.01, ctx, adapters, empty_ledger)
    rec_b = _exec_record_with_value("b", 0.03, ctx, adapters, empty_ledger)
    corpus = Corpus(
        claims=(make_claim("a", status=Status.LICENSED), make_claim("b", status=Status.LICENSED)),
        fdr_ledger=empty_ledger,
    )
    scaffolding = CycleScaffolding(grounded_extension=("a", "b"))
    out_fwd, _ = integrate(corpus, scaffolding, (rec_a, rec_b))
    out_rev, _ = integrate(corpus, scaffolding, (rec_b, rec_a))
    # ledger is unchanged in both directions
    assert out_fwd.fdr_ledger == empty_ledger
    assert out_rev.fdr_ledger == empty_ledger


def test_string_terminal_does_not_affect_ledger(empty_ledger):
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
    assert out.fdr_ledger.n_tests == 0  # ledger unchanged
    assert skipped == ()                # no skipping in the new integrate
