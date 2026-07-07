"""Duhem consistency fold: sheaf H¹ frustration obstructions demote the LICENSED claims they
implicate to PENDING duhem_underdetermined, reversibly.

Warrant-only and ledger-neutral: an H¹ contradiction does not entail any claim's effect-null
(Refund-Validity §6/§8; epistemic-core §5), so this de-licenses in the graph but leaves the
FDRTest live — it never calls retract_tests and never mutates fdr_ledger. Demote-only: never
REJECTED. Non-localizable blame (no local witness) → PENDING duhem_underdetermined, not a defeat
edge.
"""
from __future__ import annotations

from collections.abc import Sequence

from polymer_grammar import Claim, PendingReason, Status

from .base import _Model
from .blame_bridge import blame_verdict_from_obstructions
from .corpus import Corpus
from .sheaf import Obstruction, extract_sheaf, frustration_obstructions


class DuhemFoldAudit(_Model):
    demoted: tuple[str, ...] = ()
    reopened: tuple[str, ...] = ()
    contradiction_ids: tuple[str, ...] = ()


def _demote_duhem(c: Claim) -> Claim:
    """LICENSED → PENDING duhem_underdetermined; clear licensing. Mirrors integrate._reject, but
    to PENDING (reversible), not REJECTED. Ledger is not touched (warrant-only)."""
    return Claim.model_validate(
        c.model_copy(
            update={
                "status": Status.PENDING,
                "licensing": None,
                "pending_reason": PendingReason.DUHEM_UNDERDETERMINED,
                "rejection_reason": None,
            }
        ).model_dump()
    )


def _reopen_duhem(c: Claim) -> Claim:
    """A duhem-suspended claim whose cycle has resolved → PENDING reinstated, to re-test. Mirrors
    integrate._reinstate."""
    return Claim.model_validate(
        c.model_copy(
            update={
                "status": Status.PENDING,
                "licensing": None,
                "pending_reason": PendingReason.REINSTATED,
                "rejection_reason": None,
            }
        ).model_dump()
    )


def duhem_fold_from_obstructions(
    corpus: Corpus, obstructions: Sequence[Obstruction]
) -> tuple[Corpus, DuhemFoldAudit]:
    """Demote LICENSED claims implicated by any obstruction to PENDING duhem_underdetermined;
    reopen PENDING-duhem claims no longer implicated. Ledger untouched (warrant-only)."""
    implicated = blame_verdict_from_obstructions(obstructions).possibly_blamed
    demoted: list[str] = []
    reopened: list[str] = []
    new_claims: list[Claim] = []
    for c in corpus.claims:
        if c.status == Status.LICENSED and c.id in implicated:
            new_claims.append(_demote_duhem(c))
            demoted.append(c.id)
        elif (
            c.status == Status.PENDING
            and c.pending_reason == PendingReason.DUHEM_UNDERDETERMINED
            and c.id not in implicated
        ):
            new_claims.append(_reopen_duhem(c))
            reopened.append(c.id)
        else:
            new_claims.append(c)
    contradiction_ids = tuple(
        "h1:" + "|".join(sorted(o.claim_ids)) for o in obstructions
    )
    audit = DuhemFoldAudit(
        demoted=tuple(sorted(demoted)),
        reopened=tuple(sorted(reopened)),
        contradiction_ids=tuple(sorted(contradiction_ids)),
    )
    return corpus.model_copy(update={"claims": tuple(new_claims)}), audit


def apply_duhem_consistency(corpus: Corpus) -> tuple[Corpus, DuhemFoldAudit]:
    """Detect frustration obstructions from the corpus's sheaf, then apply the fold. Self-contained
    entry point for run_cycle."""
    obstructions = frustration_obstructions(extract_sheaf(corpus))
    return duhem_fold_from_obstructions(corpus, obstructions)
