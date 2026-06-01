"""Claim status lifecycle and typed PENDING reason-codes (spec §3.5)."""
from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    CONJECTURED = "conjectured"
    EXPLORATORY = "exploratory"
    PENDING = "pending"
    LICENSED = "licensed"
    REJECTED = "rejected"


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
