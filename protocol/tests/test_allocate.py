from __future__ import annotations

from polymer_protocol.allocate import CREDIT_FLOOR_DEFAULT, allocate_subcaps
from polymer_protocol.ledger import OperatorCredit, SelectionLedger


def _ledger(**rates):
    # rates: operator_id -> (n_grounded, n_high_eig)
    credits = tuple(
        OperatorCredit(operator_id=op, n_grounded=g, n_high_eig=h) for op, (g, h) in rates.items()
    )
    return SelectionLedger(credits=credits)


def test_default_floor_is_half():
    assert CREDIT_FLOOR_DEFAULT == 0.5


def test_proportional_split_among_healthy():
    # rival credit_factor = (8+1)/(9+1)=0.9 ; frontier untracked -> 1.0 ; both healthy
    led = _ledger(**{"rival-generation": (8, 9)})
    caps = allocate_subcaps(("rival-generation", "frontier-attack"), 10, led, floor=0.5)
    assert sum(caps.values()) == 10
    assert caps == {"rival-generation": 5, "frontier-attack": 5}


def test_below_floor_operator_gets_one_probation_slot():
    # frontier credit_factor = (0+1)/(4+1)=0.2 < 0.5 -> probation ; rival untracked -> 1.0 healthy
    led = _ledger(**{"frontier-attack": (0, 4)})
    caps = allocate_subcaps(("rival-generation", "frontier-attack"), 10, led, floor=0.5)
    assert caps["frontier-attack"] == 1
    assert caps["rival-generation"] == 9
    assert sum(caps.values()) == 10


def test_all_below_floor_round_robin_leftover():
    led = _ledger(**{"a": (0, 9), "b": (0, 9)})   # both 0.1 < floor
    caps = allocate_subcaps(("a", "b"), 5, led, floor=0.5)
    assert sum(caps.values()) == 5
    assert caps["a"] == 3 and caps["b"] == 2


def test_starved_cap_seats_first_operators_in_caller_order():
    led = _ledger(**{"a": (0, 9)})  # a below floor; b, c untracked healthy
    caps = allocate_subcaps(("a", "b", "c"), 2, led, floor=0.5)
    assert caps == {"a": 1, "b": 1, "c": 0}


def test_empty_ledger_even_split():
    caps = allocate_subcaps(("a", "b"), 10, SelectionLedger(), floor=0.5)
    assert caps == {"a": 5, "b": 5}


def test_deterministic_repeated_calls():
    led = _ledger(**{"rival-generation": (8, 9)})
    args = (("rival-generation", "frontier-attack"), 10, led)
    assert allocate_subcaps(*args, floor=0.5) == allocate_subcaps(*args, floor=0.5)
