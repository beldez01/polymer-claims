import math

import pytest
from pydantic import ValidationError

from polymer_grammar.fdr import (
    FDRLedger,
    FDRTest,
    _gamma,
    elond_decisions,
    is_discovery,
    process_stream,
    process_test,
)


def test_gamma_first_term():
    assert _gamma(1) == pytest.approx(6 / math.pi**2)


def test_gamma_monotone_decreasing():
    assert _gamma(1) > _gamma(2) > _gamma(3)


def test_gamma_partial_sum_converges_to_one():
    assert sum(_gamma(j) for j in range(1, 1001)) == pytest.approx(1.0, abs=1e-2)


def test_empty_ledger_properties():
    led = FDRLedger(target_fdr=0.05)
    assert led.n_tests == 0
    assert led.n_discoveries == 0
    assert led.discoveries == frozenset()
    assert led.procedure == "elond"


def test_ledger_properties_over_tests():
    led = FDRLedger(target_fdr=0.05, tests=(
        FDRTest(index=1, claim_id="a", e_value=100.0, alpha_allocated=0.03, discovery=True),
        FDRTest(index=2, claim_id="b", e_value=0.5, alpha_allocated=0.01, discovery=False),
    ))
    assert led.n_tests == 2
    assert led.n_discoveries == 1
    assert led.discoveries == frozenset({"a"})


def test_process_test_elond_rule():
    led = process_test(FDRLedger(target_fdr=0.05), "a", 40.0)
    t = led.tests[0]
    assert t.discovery is True
    assert t.e_value == 40.0
    assert t.alpha_allocated == pytest.approx(0.05 * _gamma(1) * 1)


def test_process_test_below_bar_is_not_discovery():
    led = process_test(FDRLedger(target_fdr=0.05), "a", 5.0)
    assert led.tests[0].discovery is False
    assert led.n_discoveries == 0


def test_process_stream_folds_in_order():
    led = process_stream(FDRLedger(target_fdr=0.05), [("a", 40.0), ("b", 40.0)])
    assert led.n_tests == 2
    assert led.tests[1].alpha_allocated == pytest.approx(0.05 * _gamma(2) * 2)


def test_elond_decisions_matches_iterated_process_test():
    base = FDRLedger(target_fdr=0.05)
    items = [("b", 40.0), ("a", 1.0)]  # deliberately unsorted
    new_led, decisions = elond_decisions(base, items)
    expected = process_stream(base, sorted(items))
    assert new_led.tests == expected.tests
    assert decisions == {"a": False, "b": False}


def test_validators_reject_negative_evalue():
    with pytest.raises(ValidationError):
        FDRTest(index=1, claim_id="a", e_value=-0.1, alpha_allocated=0.1, discovery=False)
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=0.0)
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=1.5)


def test_models_frozen_and_hashable():
    t = FDRTest(index=1, claim_id="a", e_value=40.0, alpha_allocated=0.03, discovery=True)
    assert isinstance(hash(t), int)
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=0.05, bogus=1)


def test_is_discovery():
    led = process_test(FDRLedger(target_fdr=0.05), "a", 40.0)
    assert is_discovery(led, "a") is True
    assert is_discovery(led, "z") is False
