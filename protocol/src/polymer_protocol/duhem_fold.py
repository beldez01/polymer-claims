"""Duhem consistency fold: sheaf H¹ frustration obstructions demote the LICENSED claims they
implicate to PENDING duhem_underdetermined, reversibly.

Warrant-only and ledger-neutral: an H¹ contradiction does not entail any claim's effect-null
(Refund-Validity §6/§8; epistemic-core §5), so this de-licenses in the graph but leaves the
FDRTest live — it never calls retract_tests and never mutates fdr_ledger. Demote-only: never
REJECTED. Non-localizable blame (no local witness) → PENDING duhem_underdetermined, not a defeat
edge.
"""
from __future__ import annotations

from collections.abc import Sequence, Set as AbstractSet

from polymer_grammar import Claim, PendingReason, Status

from .base import _Model
from .corpus import Corpus
from .sheaf import Obstruction, extract_sheaf, frustrated_vertices, frustration_obstructions


class DuhemFoldAudit(_Model):
    """`contradiction_ids` is best-effort display-only *named cycles* and may not enumerate every
    demoted/held claim; the authoritative sets are `demoted`/`reopened`."""

    demoted: tuple[str, ...] = ()
    reopened: tuple[str, ...] = ()
    # EFFECTIVE obstructions only (those that drove a demotion this fold) — a claim held PENDING
    # by a structural-only cycle (e.g. one closed by a de-licensed/inert attack) won't appear here.
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


def duhem_fold(
    corpus: Corpus,
    effective_frustrated: AbstractSet[str],
    structural_frustrated: AbstractSet[str],
    effective_obstructions: Sequence[Obstruction],
) -> tuple[Corpus, DuhemFoldAudit]:
    """Demote LICENSED claims that lie on an EFFECTIVE frustrated cycle; reopen PENDING-duhem claims
    that lie on NO STRUCTURAL frustrated cycle anywhere (the conservative, provenance-free policy).
    `effective_obstructions` is used only for the audit's display-only `contradiction_ids`."""
    demoted: list[str] = []
    reopened: list[str] = []
    new_claims: list[Claim] = []
    for c in corpus.claims:
        if c.status == Status.LICENSED and c.id in effective_frustrated:
            new_claims.append(_demote_duhem(c))
            demoted.append(c.id)
        elif (
            c.status == Status.PENDING
            and c.pending_reason == PendingReason.DUHEM_UNDERDETERMINED
            and c.id not in structural_frustrated
        ):
            new_claims.append(_reopen_duhem(c))
            reopened.append(c.id)
        else:
            new_claims.append(c)
    contradiction_ids = tuple(
        "h1:" + "|".join(sorted(o.claim_ids)) for o in effective_obstructions
    )
    audit = DuhemFoldAudit(
        demoted=tuple(sorted(demoted)),
        reopened=tuple(sorted(reopened)),
        contradiction_ids=tuple(sorted(contradiction_ids)),
    )
    return corpus.model_copy(update={"claims": tuple(new_claims)}), audit


def apply_duhem_consistency(corpus: Corpus) -> tuple[Corpus, DuhemFoldAudit]:
    """Compute effective and structural frustrated-vertex sets from the corpus's sheaf, then apply
    the fold. Self-contained entry point for run_cycle."""
    eff_sheaf = extract_sheaf(corpus)
    struct_sheaf = extract_sheaf(corpus, effective_only=False)
    return duhem_fold(
        corpus,
        frustrated_vertices(eff_sheaf),
        frustrated_vertices(struct_sheaf),
        frustration_obstructions(eff_sheaf),
    )
