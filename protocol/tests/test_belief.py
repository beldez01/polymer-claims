from polymer_grammar import StrengthVector

from polymer_protocol.belief import (
    Beta,
    accumulated_belief,
    expected_information_gain,
    prior_belief,
)
from polymer_protocol.ledger import ClaimOutcome, SelectionLedger
from tests.conftest import make_claim


def test_prior_for_none_strength_is_uniform():
    c = make_claim("a")  # strength defaults to None
    assert prior_belief(c) == Beta(alpha=1.0, beta=1.0)


def test_prior_mean_tracks_evidence_against_null():
    # high evidence_against_null, high certainty -> mean high, concentrated
    sv = StrengthVector(magnitude=0.5, certainty=1.0, evidence_against_null=0.8,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    c = make_claim("a", strength=sv)
    b = prior_belief(c)
    # kappa = 2 + (20-2)*1.0 = 20 ; alpha = 0.8*20 = 16 ; beta = 0.2*20 = 4
    assert b.alpha == 16.0
    assert b.beta == 4.0
    assert abs(b.alpha / (b.alpha + b.beta) - 0.8) < 1e-9


def test_prior_concentration_drops_with_uncertainty():
    sv = StrengthVector(magnitude=0.5, certainty=0.0, evidence_against_null=0.5,
                        severity=0.5, world_contact=0.5, explanatory_virtue=0.5)
    c = make_claim("a", strength=sv)
    b = prior_belief(c)
    # kappa = 2 + 18*0.0 = 2 ; alpha = beta = 1.0
    assert b.alpha == 1.0 and b.beta == 1.0


def test_beta_is_frozen_and_proper():
    b = Beta(alpha=2.0, beta=3.0)
    import pytest
    with pytest.raises(Exception):
        b.alpha = 5.0  # frozen
    # floor keeps it proper even for extreme strength
    sv = StrengthVector(magnitude=0.0, certainty=1.0, evidence_against_null=1.0,
                        severity=0.0, world_contact=0.0, explanatory_virtue=0.0)
    pb = prior_belief(make_claim("a", strength=sv))
    assert pb.alpha > 0.0 and pb.beta > 0.0  # beta floored above 0 despite mean=1.0


def test_eig_of_uniform_is_maximal():
    eig_uniform = expected_information_gain(Beta(alpha=1.0, beta=1.0))
    eig_concentrated = expected_information_gain(Beta(alpha=50.0, beta=50.0))
    eig_certain = expected_information_gain(Beta(alpha=100.0, beta=1.0))
    assert eig_uniform > eig_concentrated > eig_certain
    assert eig_uniform > 0.0


def test_eig_is_bounded_and_nonnegative():
    for b in [Beta(alpha=1.0, beta=1.0), Beta(alpha=2.0, beta=8.0),
              Beta(alpha=0.5, beta=0.5), Beta(alpha=30.0, beta=30.0)]:
        eig = expected_information_gain(b)
        assert 0.0 <= eig <= 1.0 + 1e-9


def test_eig_is_deterministic():
    b = Beta(alpha=3.0, beta=7.0)
    assert expected_information_gain(b) == expected_information_gain(b)


def test_accumulated_belief_is_prior_for_fresh_claim():
    c = make_claim("a")  # strength None -> prior Beta(1,1)
    assert accumulated_belief(c, SelectionLedger()) == Beta(alpha=1.0, beta=1.0)


def test_accumulated_belief_adds_outcomes():
    c = make_claim("a")  # prior Beta(1,1)
    led = SelectionLedger(outcomes=(ClaimOutcome(claim_id="a", successes=3, failures=2),))
    b = accumulated_belief(c, led)
    assert b.alpha == 4.0 and b.beta == 3.0  # 1+3, 1+2


def test_eig_settled_concentration_returns_zero():
    assert expected_information_gain(Beta(alpha=150.0, beta=150.0)) == 0.0  # alpha+beta=300 >= 200
    assert expected_information_gain(Beta(alpha=50.0, beta=50.0)) >= 0.0    # alpha+beta=100 < 200, still computed
