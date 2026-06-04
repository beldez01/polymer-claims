import pytest
from polymer_grammar import GenerationMode, Provenance

from polymer_protocol.ledger import (
    ClaimOutcome, ExecutedOutcome, OperatorCredit, SelectionLedger, credit_factor,
    operator_of, update_ledger,
)
from tests.conftest import make_claim


def test_ledger_lookups():
    led = SelectionLedger(
        outcomes=(ClaimOutcome(claim_id="a", successes=2, failures=1),),
        credits=(OperatorCredit(operator_id="op", n_high_eig=3, n_grounded=1),),
    )
    assert led.outcome("a").successes == 2
    assert led.outcome("missing") is None
    assert led.credit("op").n_grounded == 1
    assert led.credit("missing") is None


def test_ledger_rejects_duplicate_ids():
    with pytest.raises(Exception):
        SelectionLedger(outcomes=(ClaimOutcome(claim_id="a"), ClaimOutcome(claim_id="a")))
    with pytest.raises(Exception):
        SelectionLedger(credits=(OperatorCredit(operator_id="x"), OperatorCredit(operator_id="x")))


def test_operator_of_uses_agent_id_for_agent_generated():
    prov = Provenance(generated_by=GenerationMode.AGENT_GENERATED, agent_id="rival-generation",
                      search_cardinality=1)
    c = make_claim("a", provenance=prov)
    assert operator_of(c) == "rival-generation"


def test_operator_of_is_exogenous_otherwise():
    assert operator_of(make_claim("a")) == "exogenous"  # provenance None
    prov = Provenance(generated_by=GenerationMode.IMPORTED, search_cardinality=1)
    assert operator_of(make_claim("b", provenance=prov)) == "exogenous"


def test_credit_factor_optimistic_untracked_is_one():
    assert credit_factor(SelectionLedger(), "anyop") == 1.0


def test_credit_factor_penalizes_failures():
    led = SelectionLedger(credits=(OperatorCredit(operator_id="bad", n_high_eig=10, n_grounded=0),))
    cf = credit_factor(led, "bad")
    assert 0.0 < cf < 0.2  # (0 + 1)/(10 + 1) ~= 0.09
    led2 = SelectionLedger(credits=(OperatorCredit(operator_id="good", n_high_eig=10, n_grounded=10),))
    assert credit_factor(led2, "good") == 1.0


def test_update_ledger_bumps_claim_outcomes():
    out = [
        ExecutedOutcome(claim_id="a", operator_id="op", eig=0.9, licensed=True, rejected=False),
        ExecutedOutcome(claim_id="a", operator_id="op", eig=0.9, licensed=False, rejected=True),
    ]
    led = update_ledger(SelectionLedger(), tuple(out))
    o = led.outcome("a")
    assert o.successes == 1 and o.failures == 1


def test_update_ledger_high_eig_credits_only():
    out = [
        ExecutedOutcome(claim_id="a", operator_id="op", eig=0.9, licensed=True, rejected=False),  # high
        ExecutedOutcome(claim_id="b", operator_id="op", eig=0.1, licensed=False, rejected=True),  # low
    ]
    led = update_ledger(SelectionLedger(), tuple(out))
    cr = led.credit("op")
    assert cr.n_high_eig == 1   # only the eig>=HIGH_EIG one
    assert cr.n_grounded == 1


def test_update_ledger_undetermined_is_neither():
    out = (ExecutedOutcome(claim_id="a", operator_id="op", eig=0.9, licensed=False, rejected=False),)
    led = update_ledger(SelectionLedger(), out)
    o = led.outcome("a")
    assert o.successes == 0 and o.failures == 0  # undetermined: no outcome bump
    assert led.credit("op").n_high_eig == 1 and led.credit("op").n_grounded == 0  # but credit counts the miss


def test_update_ledger_merges_existing():
    led0 = SelectionLedger(outcomes=(ClaimOutcome(claim_id="a", successes=1),))
    out = (ExecutedOutcome(claim_id="a", operator_id="op", eig=0.1, licensed=True, rejected=False),)
    led = update_ledger(led0, out)
    assert led.outcome("a").successes == 2  # merged, not replaced


def test_update_ledger_deterministic():
    out = (ExecutedOutcome(claim_id="b", operator_id="op", eig=0.9, licensed=True, rejected=False),
           ExecutedOutcome(claim_id="a", operator_id="op2", eig=0.9, licensed=True, rejected=False))
    assert update_ledger(SelectionLedger(), out) == update_ledger(SelectionLedger(), out)


def test_public_exports():
    import polymer_protocol as p
    for name in ["SelectionLedger", "ClaimOutcome", "OperatorCredit", "ExecutedOutcome",
                 "operator_of", "credit_factor", "update_ledger", "accumulated_belief", "cell_of"]:
        assert hasattr(p, name), name
