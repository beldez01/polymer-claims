"""Claim status lifecycle and typed PENDING reason-codes (spec §3.5)."""
from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    CONJECTURED = "conjectured"
    EXPLORATORY = "exploratory"
    PENDING = "pending"
    LICENSED = "licensed"
    REJECTED = "rejected"
    STRUCTURAL = "structural"   # true by construction (e.g. a structural-key equivalence);
                                # NOT an evidential license. Valid only on EquivalenceClaim.


class PendingReason(str, Enum):
    UNTESTED = "untested"
    UNDERPOWERED = "underpowered"
    EXPLORATORY_BY_DESIGN = "exploratory_by_design"
    CONTESTED = "contested"
    DUHEM_UNDERDETERMINED = "duhem_underdetermined"
    DEFINITIONAL_COMMITMENT_CONTESTED = "definitional_commitment_contested"
    ONTOLOGY_TERM_OBSOLETE = "ontology_term_obsolete"
    STRENGTH_INCOMPARABLE = "strength_incomparable"
    UNREPRODUCIBLE_BY_GOVERNANCE = "unreproducible_by_governance"
    MATERIALIZATION_DRIFTED = "materialization_drifted"
    # verify withheld a license: the agreeing adapters are not registry-independent
    ADAPTER_NOT_INDEPENDENT = "adapter_not_independent"
    # a defeat-rejected claim whose attacker was itself defeated: reopened to re-test (reinstatement)
    REINSTATED = "reinstated"
    # verify withheld a license under strict_shared_cause: the hypothesis prior shares a cohort
    # with the test data (confirmatory, not a held-out severe test)
    SHARED_CAUSE_CONFIRMATORY = "shared_cause_confirmatory"
    # the evidence execution pipeline raised an unrecoverable error
    EXECUTION_ERROR = "execution_error"


class RejectionReason(str, Enum):
    """The one-way counterpart to PendingReason — records why a claim is REJECTED; a REJECTED claim
    is NOT required to carry one (back-compat). The protocol decides which causes are reinstatable;
    only DEFEAT_GROUNDED_OUT is (its attacker may later fall)."""

    DEFEAT_GROUNDED_OUT = "defeat_grounded_out"   # knocked out of the grounded extension by an attacker
    REFUTED = "refuted"                           # the data refuted it (terminal)
    ROBUSTLY_BLAMED = "robustly_blamed"           # Duhem robust blame (terminal; reserved, not yet wired)
    HYPOTHESIS_ALTERED = "hypothesis_altered"     # plan changed after pre-registration (terminal)


def check_pending_reason(status: Status, pending_reason: PendingReason | None) -> None:
    """Enforce the PENDING iff pending_reason invariant; raises ValueError on violation.
    Shared by Claim and EquivalenceClaim."""
    if status == Status.PENDING and pending_reason is None:
        raise ValueError("status=PENDING requires a `pending_reason`")
    if status != Status.PENDING and pending_reason is not None:
        raise ValueError(
            f"`pending_reason` is only valid when status=PENDING; "
            f"got status={status.value}"
        )
