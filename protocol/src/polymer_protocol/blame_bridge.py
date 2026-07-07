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

from polymer_grammar.blame import BlameAssignment, BlameSet, BlameVerdict
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
