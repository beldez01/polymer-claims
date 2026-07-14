"""neg-whisper ②b — independence as a defeasible claim + the multiply-gate decision.

Standalone: this does NOT modify the live licensing multiply (that wire-in is flagged for operator
review). Tests cover the claim representation (two-stratum: minted PENDING, never self-licensed), the
verdict reader, and the byte-identity of `multiply_allowed` when no independence claim is present.
"""
from __future__ import annotations

from polymer_grammar import Claim, Status

from polymer_claims.adapter_independence import CORRELATED_BIAS_DEFEATER
from polymer_claims.independence_claim import (
    independence_verdict_for,
    is_independence_claim,
    make_independence_claim,
    multiply_allowed,
)


def test_make_independence_claim_is_pending_not_self_licensed():
    c = make_independence_claim("legA", "legB", rho_cv=0.1, e_value=12.0, independent=True)
    # two-stratum: minted PENDING (evidence recorded), NOT LICENSED
    assert c.status == Status.PENDING
    assert is_independence_claim(c)
    assert c.leaves[0].rebuttal == CORRELATED_BIAS_DEFEATER  # bias residue is the standing rebuttal
    assert set((*c.subject.source_set, *c.subject.target_set)) == {"legA", "legB"}
    Claim.model_validate_json(c.model_dump_json())  # valid, round-trips


def test_distinct_legs_required():
    import pytest
    with pytest.raises(ValueError):
        make_independence_claim("x", "x", rho_cv=0.0, e_value=1.0, independent=True)


def test_verdict_absent_or_pending_is_none():
    pending = make_independence_claim("a", "b", rho_cv=0.1, e_value=9.0, independent=True)
    assert independence_verdict_for([], "a", "b") is None          # no claim
    assert independence_verdict_for([pending], "a", "b") is None   # only PENDING -> today's behavior


def test_verdict_licensed_true_rejected_false():
    lic = make_independence_claim("a", "b", rho_cv=0.05, e_value=40.0, independent=True).model_copy(
        update={"status": Status.LICENSED, "pending_reason": None}
    )
    assert independence_verdict_for([lic], "a", "b") is True
    from polymer_grammar import RejectionReason
    rej = make_independence_claim("a", "b", rho_cv=0.9, e_value=0.2, independent=False).model_copy(
        update={"status": Status.REJECTED, "pending_reason": None, "rejection_reason": RejectionReason.REFUTED}
    )
    assert independence_verdict_for([rej], "a", "b") is False
    # a refutation wins over a license (conservative): both present -> False
    assert independence_verdict_for([lic, rej], "a", "b") is False


def test_verdict_keyed_on_the_leg_pair():
    lic = make_independence_claim("a", "b", rho_cv=0.05, e_value=40.0, independent=True).model_copy(
        update={"status": Status.LICENSED, "pending_reason": None}
    )
    assert independence_verdict_for([lic], "a", "c") is None  # different pair -> no verdict


def test_multiply_allowed_byte_identical_when_no_independence_claim():
    # multiply_allowed(v, None) must equal today's `cohorts_error_independent(...) is not False`
    for v in (True, False, None):
        assert multiply_allowed(v, None) == (v is not False)


def test_multiply_allowed_withdraws_on_false_verdict():
    # independence claim says NOT independent -> withdraw the multiply even if the factor gate allows
    assert multiply_allowed(True, False) is False
    assert multiply_allowed(None, False) is False
    # independence claim says independent -> allow (subject to the factor gate)
    assert multiply_allowed(True, True) is True
    assert multiply_allowed(False, True) is False  # factor gate still vetoes
