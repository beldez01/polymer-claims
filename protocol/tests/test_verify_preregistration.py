# protocol/tests/test_verify_preregistration.py
from polymer_grammar import Comparator, MaterializationContext, RejectionReason, Status
from polymer_grammar import IdentityAdapter, ReferenceAdapter
from polymer_protocol import Corpus, register_hypotheses, run_cycle

from tests.conftest import make_claim, make_plan   # tests/ is a package (has __init__.py)

ADAPTERS = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
CTX = MaterializationContext(id="M", api_version="v1", data_version="d1")


def _run(corpus, evidence):
    return run_cycle(corpus, ADAPTERS, CTX, evidence=evidence)


def test_registered_claim_resolves_and_can_license():
    # const plan value=12 > threshold 10 -> satisfied; big e-value -> discovery at t=1
    from polymer_grammar import FDRLedger
    c = make_claim("c", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
    corpus = register_hypotheses(Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05)))
    out = _run(corpus, {"c": 1e6})
    led = out.corpus.fdr_ledger
    assert led.n_tests == 1 and led.tests[0].e_value == 1e6 and led.tests[0].discovery is True
    assert out.corpus.claims[0].status is Status.LICENSED


def test_post_hoc_alteration_is_rejected():
    # register with threshold 10, then run with the plan mutated to threshold 5 (a different hypothesis)
    from polymer_grammar import FDRLedger
    registered = make_claim("c", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
    corpus = register_hypotheses(Corpus(claims=(registered,), fdr_ledger=FDRLedger(target_fdr=0.05)))
    altered = make_claim("c", Status.PENDING, plan=make_plan(12.0, 5.0, Comparator.GT))   # same id, new plan
    corpus = corpus.model_copy(update={"claims": (altered,)})
    out = _run(corpus, {"c": 1e6})
    c_out = out.corpus.claims[0]
    assert c_out.status is Status.REJECTED
    assert c_out.rejection_reason is RejectionReason.HYPOTHESIS_ALTERED
    # the slot stays consumed and pending (never a discovery)
    assert out.corpus.fdr_ledger.tests[0].e_value is None and out.corpus.fdr_ledger.n_discoveries == 0


def test_no_registration_is_byte_identical():
    # a run WITHOUT register_hypotheses uses the existing charge-at-verify path unchanged
    from polymer_grammar import FDRLedger
    c = make_claim("c", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
    plain = Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05))
    out = _run(plain, {"c": 1e6})
    assert out.corpus.fdr_ledger.n_tests == 1 and out.corpus.fdr_ledger.tests[0].commitment_hash is None
    assert out.corpus.claims[0].status is Status.LICENSED   # identical outcome to pre-Phase-D


def test_strict_no_refund_across_a_cycle():
    # a registered claim with NO evidence this cycle keeps its pending slot (not refunded)
    from polymer_grammar import FDRLedger
    c = make_claim("c", Status.PENDING, plan=make_plan(12.0, 10.0, Comparator.GT))
    corpus = register_hypotheses(Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05)))
    out = _run(corpus, {})            # no e-value supplied -> not resolved
    assert out.corpus.fdr_ledger.n_tests == 1 and out.corpus.fdr_ledger.tests[0].e_value is None
