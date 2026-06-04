import pytest
from polymer_grammar import GenerationMode, Provenance

from polymer_protocol.ledger import (
    ClaimOutcome, OperatorCredit, SelectionLedger, credit_factor, operator_of,
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
