# grammar/tests/test_fdr_registration.py
import math

import pytest

from polymer_grammar.fdr import FDRLedger, process_test, register_test, resolve_test

Q = 0.05
G1 = (6.0 / math.pi**2)            # gamma_1


def _ledger():
    return FDRLedger(target_fdr=Q)


def test_register_appends_pending_and_locks_alpha():
    led = register_test(_ledger(), "c1", "sha256:aa")
    assert led.n_tests == 1 and led.n_discoveries == 0       # pending is not a discovery
    t = led.tests[0]
    assert t.e_value is None and t.discovery is False
    assert t.commitment_hash == "sha256:aa"
    assert t.alpha_allocated == pytest.approx(Q * G1 * 1)    # alpha locked at registration


def test_resolve_fills_evalue_and_decides_against_locked_alpha():
    led = register_test(_ledger(), "c1", "sha256:aa")
    alpha = led.tests[0].alpha_allocated
    # an e-value just above 1/alpha is a discovery; just below is not
    led_hit = resolve_test(led, "c1", 1.0 / alpha + 1.0)
    led_miss = resolve_test(led, "c1", 1.0 / alpha - 0.0001)
    assert led_hit.tests[0].discovery is True and led_hit.n_discoveries == 1
    assert led_miss.tests[0].discovery is False and led_miss.n_discoveries == 0


def test_register_then_resolve_in_order_equals_process_test():
    # soundness: a single registered+resolved test == charge-at-verify for the same single test
    e = 25.0
    via_register = resolve_test(register_test(_ledger(), "c1", "sha256:aa"), "c1", e)
    via_process = process_test(_ledger(), "c1", e)
    assert via_register.tests[0].alpha_allocated == pytest.approx(via_process.tests[0].alpha_allocated)
    assert via_register.tests[0].discovery == via_process.tests[0].discovery


def test_multiplicity_is_charged():
    # an e-value that is a discovery at t=1 is NOT a discovery at t=10 after 9 prior registrations
    led = _ledger()
    e = 1.0 / (Q * G1) + 1.0          # clears the bar at t=1
    assert resolve_test(register_test(led, "x", "h"), "x", e).tests[-1].discovery is True
    for i in range(9):
        led = register_test(led, f"r{i}", "h")     # 9 prior commitments consume slots
    led = register_test(led, "x", "h")             # x is now test t=10
    led = resolve_test(led, "x", e)
    x = next(t for t in led.tests if t.claim_id == "x")
    assert x.index == 10 and x.discovery is False   # same e, tightened bar -> withheld


def test_strict_no_refund_unexecuted_keeps_its_slot():
    led = register_test(_ledger(), "never_run", "h")   # registered, never resolved
    led = register_test(led, "c2", "h")                # c2 is test t=2, not t=1
    assert led.tests[1].index == 2
    assert led.tests[1].alpha_allocated == pytest.approx(Q * (6.0 / math.pi**2 / 4) * 1)  # gamma_2


def test_resolve_without_pending_raises():
    with pytest.raises(ValueError):
        resolve_test(_ledger(), "ghost", 10.0)


def test_pending_entry_serializes_roundtrip():
    led = register_test(_ledger(), "c1", "sha256:aa")
    again = FDRLedger.model_validate_json(led.model_dump_json())
    assert again.tests[0].e_value is None and again.tests[0].commitment_hash == "sha256:aa"


def test_out_of_order_resolution_is_conservative():
    # register A then B; resolve B (a discovery) BEFORE A. A's alpha was LOCKED at registration with
    # D=0, so it must NOT retroactively benefit from B's later discovery -> conservative (FDR<=q safe).
    led = register_test(_ledger(), "A", "h")
    led = register_test(led, "B", "h")
    a_alpha = next(t for t in led.tests if t.claim_id == "A").alpha_allocated
    led = resolve_test(led, "B", 1e6)          # B resolves first, as a discovery
    led = resolve_test(led, "A", 1e6)          # A resolves second
    a = next(t for t in led.tests if t.claim_id == "A")
    assert a.alpha_allocated == a_alpha == pytest.approx(Q * G1 * 1)   # unchanged; D was 0 at A's registration
    assert a.discovery is True
