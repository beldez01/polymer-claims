from polymer_grammar import LicenseRoute, SatisfactionVerdict, Status

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus, CycleScaffolding
from polymer_protocol.execute import execute_ground
from polymer_protocol.verify import verify_stage
from tests.conftest import make_claim, make_plan


def _run_to_records(claim, empty_ledger, ctx, adapters):
    corpus = commit(Corpus(claims=(claim,), fdr_ledger=empty_ledger))
    return execute_ground(corpus, adapters, ctx)


def test_satisfied_in_extension_becomes_licensed(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus, records = _run_to_records(c, empty_ledger, ctx, adapters)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)
    graded = out.by_id()["a"]
    assert graded.status == Status.LICENSED
    assert graded.pending_reason is None
    assert graded.licensing is not None
    assert graded.licensing.route == LicenseRoute.SEVERE_TEST
    assert graded.licensing.satisfactions[0].verdict == SatisfactionVerdict.SATISFIED


def test_satisfied_but_outside_extension_is_rejected(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus, records = _run_to_records(c, empty_ledger, ctx, adapters)
    scaffolding = CycleScaffolding(grounded_extension=())  # a is OUT
    out = verify_stage(corpus, scaffolding, records)
    assert out.by_id()["a"].status == Status.REJECTED


def test_refuted_claim_is_rejected(empty_ledger, ctx, adapters):
    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.99, 0.05))
    corpus, records = _run_to_records(c, empty_ledger, ctx, adapters)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)
    graded = out.by_id()["a"]
    assert graded.status == Status.REJECTED
    assert graded.licensing is None


def test_two_impl_disagreement_stays_pending(empty_ledger, ctx):
    from polymer_grammar import IdentityAdapter, ReferenceAdapter

    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    # perturbed reference adapter -> terminal values disagree -> no mint, disagreement set
    disagreeing = (IdentityAdapter(), ReferenceAdapter(identity="reference", perturb=10.0))
    corpus, records = execute_ground(corpus, disagreeing, ctx)
    assert records[0].evaluation.agreement is False
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, records)
    assert out.by_id()["a"].status == Status.PENDING


def test_claim_without_record_is_untouched(empty_ledger, ctx, adapters):
    executed = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    bystander = make_claim("b", status=Status.CONJECTURED)
    corpus = commit(Corpus(claims=(executed, bystander), fdr_ledger=empty_ledger))
    corpus, records = execute_ground(corpus, adapters, ctx)
    scaffolding = CycleScaffolding(grounded_extension=("a", "b"))
    out = verify_stage(corpus, scaffolding, records)
    assert out.by_id()["b"].status == Status.CONJECTURED


def test_satisfied_in_ext_but_no_provenance_stays_pending(empty_ledger, ctx):
    # A minted satisfaction without provenance must stay PENDING (selection-aware honesty gate).
    from polymer_grammar import (
        EvaluationResult, ExecValue, Satisfaction, SatisfactionVerdict, VerifiedEvaluation,
    )
    from polymer_protocol.corpus import ExecRecord

    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    assert c.provenance is None  # not committed -> no provenance
    sat = Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=ctx)
    result = EvaluationResult(
        verdict=SatisfactionVerdict.SATISFIED, terminal=ExecValue(value=0.01),
        nodes=(), adapter_identity="identity", status="complete",
    )
    ev = VerifiedEvaluation(results=(result, result), agreement=True, satisfaction=sat)
    corpus = Corpus(claims=(c,), fdr_ledger=empty_ledger)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, (ExecRecord(claim_id="a", evaluation=ev),))
    assert out.by_id()["a"].status == Status.PENDING


def test_agreed_undetermined_in_ext_stays_pending(empty_ledger, ctx):
    # Agreed UNDETERMINED (e.g. a data handle returned None) is neither licensed nor rejected.
    from polymer_grammar import EvaluationResult, ExecValue, SatisfactionVerdict, VerifiedEvaluation
    from polymer_protocol.corpus import ExecRecord

    c = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    corpus = commit(Corpus(claims=(c,), fdr_ledger=empty_ledger))
    r1 = EvaluationResult(verdict=SatisfactionVerdict.UNDETERMINED, terminal=ExecValue(value=None),
                          nodes=(), adapter_identity="identity", status="error")
    r2 = EvaluationResult(verdict=SatisfactionVerdict.UNDETERMINED, terminal=ExecValue(value=None),
                          nodes=(), adapter_identity="reference", status="error")
    ev = VerifiedEvaluation(results=(r1, r2), agreement=True, satisfaction=None)
    scaffolding = CycleScaffolding(grounded_extension=("a",))
    out = verify_stage(corpus, scaffolding, (ExecRecord(claim_id="a", evaluation=ev),))
    assert out.by_id()["a"].status == Status.PENDING
