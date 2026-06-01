"""L1 — equivalence as an asserted, defeasible claim (spec §1.2-1.3).

"Same claim?" is answered by whether a LICENSED EquivalenceClaim relates two
propositions (by content_hash) — never by structural/hash equality (Halvorson 2012).
Lightweight first-class type now; promotable to a full meta-claim once
'subject = set of claims' exists. When `grounded_in` is supplied, an edge counts as "IN" iff its id is a member of
that frozenset (real L3 grounded-extension membership). Legacy callers that omit
the kwarg fall back to LICENSED-only gating.
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

from pydantic import Field, model_validator

from .base import _Model
from .status import PendingReason, Status


class EquivalenceClaim(_Model):
    id: str
    left: str
    right: str
    severity: float = Field(ge=0.0, le=1.0)
    status: Status
    pending_reason: PendingReason | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _distinct_endpoints(self) -> "EquivalenceClaim":
        if self.left == self.right:
            raise ValueError(
                "an EquivalenceClaim must relate two DISTINCT propositions"
            )
        return self

    @model_validator(mode="after")
    def _pending_reason_iff_pending(self) -> "EquivalenceClaim":
        if self.status == Status.PENDING and self.pending_reason is None:
            raise ValueError("status=PENDING requires a `pending_reason`")
        if self.status != Status.PENDING and self.pending_reason is not None:
            raise ValueError(
                f"`pending_reason` is only valid when status=PENDING; "
                f"got status={self.status.value}"
            )
        return self


def equivalence_class(
    handle: str,
    equivalences: Iterable[EquivalenceClaim],
    *,
    grounded_in: frozenset[str] | None = None,
) -> frozenset[str]:
    """Connected component of `handle` over symmetric equivalence edges.

    An edge counts as "IN" when, if `grounded_in` is supplied, its claim id is a member
    of that grounded extension (the real L3 membership); otherwise (back-compat) when its
    status is LICENSED.
    """
    adj: dict[str, set[str]] = defaultdict(set)
    for eq in equivalences:
        counts = (
            eq.id in grounded_in
            if grounded_in is not None
            else eq.status == Status.LICENSED
        )
        if counts:
            adj[eq.left].add(eq.right)
            adj[eq.right].add(eq.left)
    seen = {handle}
    queue: deque[str] = deque([handle])
    while queue:
        node = queue.popleft()
        for nbr in adj[node]:
            if nbr not in seen:
                seen.add(nbr)
                queue.append(nbr)
    return frozenset(seen)


def are_equivalent(
    a: str,
    b: str,
    equivalences: Iterable[EquivalenceClaim],
    *,
    grounded_in: frozenset[str] | None = None,
) -> bool:
    """Reflexive / symmetric / transitive over IN equivalence edges (see equivalence_class)."""
    return b in equivalence_class(a, equivalences, grounded_in=grounded_in)
