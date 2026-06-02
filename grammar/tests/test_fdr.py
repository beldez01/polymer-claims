import math

import pytest
from pydantic import ValidationError

from polymer_grammar.fdr import (
    FDRLedger,
    FDRTest,
    _gamma,
    is_discovery,
    process_stream,
    process_test,
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


def test_process_first_test_discovery():
    led = process_test(FDRLedger(target_fdr=0.5), "c1", 0.30)
    assert led.n_tests == 1
    t = led.tests[0]
    assert t.index == 1
    assert t.alpha_allocated == pytest.approx(0.5 * (6 / math.pi**2))   # target·γ_1·1 ≈ 0.304
    assert t.discovery is True                                          # 0.30 <= ~0.304


def test_process_first_test_non_discovery():
    led = process_test(FDRLedger(target_fdr=0.5), "c1", 0.50)
    assert led.tests[0].discovery is False                             # 0.50 > ~0.304


def test_budget_grows_with_discoveries():
    # Stream A: test 1 is a discovery -> D=1 raises the budget, so a borderline p=0.10
    # at test 2 (α_2 = 0.5·γ_2·2 ≈ 0.152) PASSES.
    a = process_test(process_test(FDRLedger(target_fdr=0.5), "c1", 0.30), "c2", 0.10)
    assert a.discoveries == frozenset({"c1", "c2"})
    # Stream B: test 1 fails (0.50 > ~0.304) -> D stays 0, so the SAME p=0.10 at test 2
    # (α_2 = 0.5·γ_2·1 ≈ 0.076) FAILS.
    b = process_test(process_test(FDRLedger(target_fdr=0.5), "x1", 0.50), "c2", 0.10)
    assert b.discoveries == frozenset()


def test_process_stream_equals_iterated_process_test():
    items = [("a", 0.01), ("b", 0.40), ("c", 0.02)]
    streamed = process_stream(FDRLedger(target_fdr=0.1), items)
    manual = FDRLedger(target_fdr=0.1)
    for cid, p in items:
        manual = process_test(manual, cid, p)
    assert streamed.tests == manual.tests


def test_is_discovery_query():
    led = process_test(FDRLedger(target_fdr=0.5), "c1", 0.30)   # discovery
    led = process_test(led, "c2", 0.99)                         # not a discovery
    assert is_discovery(led, "c1") is True
    assert is_discovery(led, "c2") is False
    assert is_discovery(led, "absent") is False


def test_public_api_exports():
    import polymer_grammar as pg

    for name in ["FDRTest", "FDRLedger", "process_test", "process_stream", "is_discovery"]:
        assert hasattr(pg, name), f"{name} not exported from polymer_grammar"
