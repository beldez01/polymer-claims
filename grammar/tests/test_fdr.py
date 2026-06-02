import math

import pytest
from pydantic import ValidationError

from polymer_grammar.fdr import (
    FDRLedger,
    FDRTest,
    _gamma,
)


def test_gamma_first_term():
    assert _gamma(1) == pytest.approx(6 / math.pi**2)


def test_gamma_monotone_decreasing():
    assert _gamma(1) > _gamma(2) > _gamma(3)


def test_gamma_partial_sum_converges_to_one():
    # Σ_{j≥1} (6/π²)/j² = 1 (Basel); first 1000 terms get within 1e-2.
    assert sum(_gamma(j) for j in range(1, 1001)) == pytest.approx(1.0, abs=1e-2)


def test_empty_ledger_properties():
    led = FDRLedger(target_fdr=0.05)
    assert led.n_tests == 0
    assert led.n_discoveries == 0
    assert led.discoveries == frozenset()
    assert led.procedure == "lond"


def test_ledger_properties_over_tests():
    led = FDRLedger(target_fdr=0.05, tests=(
        FDRTest(index=1, claim_id="a", p_value=0.01, alpha_allocated=0.03, discovery=True),
        FDRTest(index=2, claim_id="b", p_value=0.40, alpha_allocated=0.01, discovery=False),
    ))
    assert led.n_tests == 2
    assert led.n_discoveries == 1
    assert led.discoveries == frozenset({"a"})


def test_validators_reject_out_of_range():
    with pytest.raises(ValidationError):
        FDRTest(index=1, claim_id="a", p_value=1.5, alpha_allocated=0.1, discovery=False)
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=0.0)     # must be > 0
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=1.5)     # must be <= 1


def test_models_frozen_and_hashable():
    t = FDRTest(index=1, claim_id="a", p_value=0.01, alpha_allocated=0.03, discovery=True)
    assert isinstance(hash(t), int)
    with pytest.raises(ValidationError):
        FDRLedger(target_fdr=0.05, bogus=1)
