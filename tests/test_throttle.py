from polymer_claims.throttle import every_n_ticks


def test_every_n_ticks_fires_on_multiples():
    calls = []
    inner = lambda corpus, frontier: (calls.append(1), ("proposal",))[1]  # noqa: E731  # returns a 1-tuple
    p = every_n_ticks(inner, n=3)
    out = [p(None, ()) for _ in range(7)]   # ticks 1..7
    # fires on the 1st call then every 3rd: ticks 1,4,7 -> non-empty; others empty
    assert [bool(o) for o in out] == [True, False, False, True, False, False, True]
    assert len(calls) == 3


def test_every_n_ticks_n_one_is_passthrough():
    """n=1 means fire every call — pure pass-through."""
    calls = []
    inner = lambda corpus, frontier: (calls.append(1), ("proposal",))[1]  # noqa: E731
    p = every_n_ticks(inner, n=1)
    out = [p(None, ()) for _ in range(5)]
    assert all(bool(o) for o in out)
    assert len(calls) == 5


def test_every_n_ticks_returns_callable_with_right_shape():
    """Returned wrapper is callable and produces tuple output."""
    inner = lambda corpus, frontier: ("a", "b")  # noqa: E731
    p = every_n_ticks(inner, n=2)
    result = p(None, ())   # tick 1 — should fire
    assert callable(p)
    assert isinstance(result, tuple)
    assert result == ("a", "b")
