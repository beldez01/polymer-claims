"""Per-operator generation budget allocation (#4b slice-2, spec §4.1).

Splits the global generation cap into per-operator sub-caps by SelectionLedger credit:
above-floor operators share the budget proportional to credit_factor (largest-remainder,
deterministic); a below-floor operator is throttled to a single recoverable probation slot
(never killed). Caller order breaks every tie. Pure, deterministic. Spec §4.
"""
from __future__ import annotations

from .ledger import SelectionLedger, credit_factor

CREDIT_FLOOR_DEFAULT = 0.5  # an operator grounding <~half its high-EIG bets (smoothed) is on probation


def allocate_subcaps(
    operator_ids: tuple[str, ...],
    cap: int,
    ledger: SelectionLedger,
    *,
    floor: float,
) -> dict[str, int]:
    ops = tuple(operator_ids)
    if not ops or cap <= 0:
        return {op: 0 for op in ops}

    cf = {op: credit_factor(ledger, op) for op in ops}

    # Starved: cannot seat even one slot per operator -> first `cap` in caller order get 1.
    if cap <= len(ops):
        return {op: (1 if i < cap else 0) for i, op in enumerate(ops)}

    below = [op for op in ops if cf[op] < floor]
    healthy = [op for op in ops if cf[op] >= floor]
    subcaps = {op: 1 for op in below}  # probation slot each
    remaining = cap - len(below)

    if not healthy:
        for i in range(remaining):
            subcaps[below[i % len(below)]] += 1
        return {op: subcaps.get(op, 0) for op in ops}

    total_w = sum(cf[op] for op in healthy)
    exact = {op: remaining * cf[op] / total_w for op in healthy}
    floors = {op: int(exact[op]) for op in healthy}
    leftover = remaining - sum(floors.values())
    order = sorted(healthy, key=lambda op: (-(exact[op] - floors[op]), ops.index(op)))
    for op in order[:leftover]:
        floors[op] += 1
    subcaps.update(floors)
    return {op: subcaps.get(op, 0) for op in ops}
