"""Bridge H¹ frustration obstructions to Duhem–Quine blame verdicts.

A frustrated cycle (sheaf H¹, epistemology.md §6) is a contradiction with NO local witness:
every edge looks locally consistent but the cycle does not close. Duhem–Quine: blame can fall
on any member of the bundle, and nothing isolates the culprit. So a single cycle maps to one
singleton candidate-repair per member -> aggregate_blame's intersection is empty -> every member
is `underdetermined` -> PENDING duhem_underdetermined. A claim present in EVERY obstruction across
>=2 obstructions is the robustly-blamed common cause -> REJECTED / ROBUSTLY_BLAMED.

Pure: pydantic + stdlib only; no numpy, no polymer_claims. The numpy detector that produces the
Obstructions lives in the umbrella (`polymer_claims.sheaf_spectrum`); this module never runs it.
"""
from __future__ import annotations

from collections.abc import Sequence

from polymer_grammar.blame import (
    BlameAssignment,
    BlameSet,
    BlameVerdict,
    duhem_rejection_reason,
    duhem_status,
)
from polymer_grammar.status import PendingReason, RejectionReason, Status

from .sheaf import Obstruction


def blame_set_from_obstruction(obs: Obstruction) -> BlameSet:
    """One singleton candidate-repair per cycle member: no local witness, so no member is
    blamed in every repair -> aggregate_blame leaves them all underdetermined."""
    members = sorted(obs.claim_ids)
    return BlameSet(
        contradiction_id="h1:" + "|".join(members),
        assignments=tuple(BlameAssignment(targets=(cid,)) for cid in members),
    )


def blame_verdict_from_obstructions(obstructions: Sequence[Obstruction]) -> BlameVerdict:
    """Aggregate blame across frustrated cycles. A claim in EVERY obstruction (>=2 of them) is the
    robustly-blamed common culprit; a single cycle has no local witness so nothing is robust."""
    member_sets = list(dict.fromkeys(frozenset(o.claim_ids) for o in obstructions))
    if not member_sets:
        empty: frozenset[str] = frozenset()
        return BlameVerdict(robustly_blamed=empty, possibly_blamed=empty, underdetermined=empty)
    union = frozenset().union(*member_sets)
    robust = frozenset.intersection(*member_sets) if len(member_sets) >= 2 else frozenset()
    return BlameVerdict(
        robustly_blamed=robust,
        possibly_blamed=union,
        underdetermined=union - robust,
    )


def duhem_statuses_from_obstructions(
    obstructions: Sequence[Obstruction],
) -> dict[str, tuple[Status, PendingReason | None, RejectionReason | None]]:
    """Per-claim (status, pending_reason, rejection_reason) for every claim implicated by the
    obstructions. Underdetermined -> PENDING duhem_underdetermined; robustly blamed -> REJECTED
    robustly_blamed. Claims not implicated are absent from the dict."""
    verdict = blame_verdict_from_obstructions(obstructions)
    out: dict[str, tuple[Status, PendingReason | None, RejectionReason | None]] = {}
    for cid in sorted(verdict.possibly_blamed):
        mapped = duhem_status(cid, verdict)
        if mapped is None:
            # defensive: unreachable for verdicts from blame_verdict_from_obstructions
            # (possibly_blamed == underdetermined ∪ robustly_blamed), kept for hand-built verdicts.
            continue
        status, pending_reason = mapped
        out[cid] = (status, pending_reason, duhem_rejection_reason(cid, verdict))
    return out
