# protocol/tests/test_register_hypotheses.py
from polymer_grammar import Comparator, Status
from polymer_protocol import Corpus, register_hypotheses

from tests.conftest import make_claim, make_plan


def _corpus(*claims):
    from polymer_grammar import FDRLedger
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_registers_one_pending_entry_per_claim_sorted():
    c_b = make_claim("b", Status.CONJECTURED, plan=make_plan(0.2, 0.1, Comparator.GT))
    c_a = make_claim("a", Status.CONJECTURED, plan=make_plan(0.2, 0.1, Comparator.GT))
    out = register_hypotheses(_corpus(c_b, c_a))
    led = out.fdr_ledger
    assert led.n_tests == 2
    assert [t.claim_id for t in led.tests] == ["a", "b"]            # claim-id-sorted, deterministic
    assert all(t.e_value is None and t.commitment_hash for t in led.tests)


def test_skips_claims_without_a_plan():
    c = make_claim("a", Status.CONJECTURED, plan=None)
    out = register_hypotheses(_corpus(c))
    assert out.fdr_ledger.n_tests == 0


def test_idempotent_no_double_charge():
    c = make_claim("a", Status.CONJECTURED, plan=make_plan(0.2, 0.1, Comparator.GT))
    once = register_hypotheses(_corpus(c))
    twice = register_hypotheses(once)
    assert twice.fdr_ledger.n_tests == 1                            # second call is a no-op for 'a'


def test_commitment_hash_recorded_matches_grammar():
    from polymer_grammar.commitment import commitment_hash
    c = make_claim("a", Status.CONJECTURED, plan=make_plan(0.2, 0.1, Comparator.GT))
    out = register_hypotheses(_corpus(c))
    assert out.fdr_ledger.tests[0].commitment_hash == commitment_hash(c)
