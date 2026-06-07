"""Stateful driver-layer utilities for controlling proposer call frequency.

This module lives in the *umbrella* package (``polymer_claims``), NOT in the pure
``polymer_protocol`` or ``polymer_grammar`` cores.  That separation is intentional:
the engine (``run_cycle``, daemons, the scheduler) is completely pure — it receives
a ``Proposer`` callable and calls it; it knows nothing about ticks.  All mutable
tick-state lives here, outside the protocol boundary, in the caller-managed driver
layer.

The primary export is :func:`every_n_ticks`, which wraps any ``Proposer`` so it
only forwards to the inner callable on the first invocation and every *n*-th
invocation thereafter — returning an empty tuple on the intervening calls.  This
produces a burst→settle rhythm: the engine can SELECT / EXECUTE / LICENSE
already-proposed claims on the quiet ticks without paying LLM latency or API cost
on every tick.
"""
from __future__ import annotations

from polymer_protocol import Proposer


def every_n_ticks(inner: Proposer, *, n: int) -> Proposer:
    """Return a :data:`~polymer_protocol.Proposer` that forwards to *inner* only every *n* calls.

    The counter starts at 0.  On each call the wrapper checks ``counter % n == 0``
    (so it fires on tick 1, tick 1+n, tick 1+2n, …) then increments.  When it does
    NOT fire it returns ``()`` so the engine's SELECT / EXECUTE / LICENSE passes can
    still run on already-queued claims.

    Parameters
    ----------
    inner:
        The proposer to throttle.  Any callable matching the ``Proposer`` protocol
        (``(Corpus, tuple[str, ...]) -> tuple[Proposal, ...]``).
    n:
        Stride.  ``n <= 1`` is treated as pass-through: *inner* is called on every
        tick (equivalent to no throttle).

    Returns
    -------
    Proposer
        A stateful wrapper.  The state (tick counter) is closed over; each call to
        :func:`every_n_ticks` produces an independent counter so multiple throttled
        proposers do not interfere.
    """
    effective_n = max(1, n)
    counter = [0]  # mutable cell in a list so the closure can mutate it

    def _throttled(corpus, frontier):
        fire = (counter[0] % effective_n) == 0
        counter[0] += 1
        if fire:
            return inner(corpus, frontier)
        return ()

    return _throttled
