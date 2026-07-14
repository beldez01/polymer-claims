"""neg-whisper ⑤ — licensed-negative morphospace: FORBIDDEN vs UNOBSERVED.

Additive: `Pattern.asserts_absence` defaults False (every existing pattern unchanged; registry-side,
not in the Corpus) and `morphospace_state` is a pure read-only classifier — the licensing gate is
untouched (a negative claim licenses through the existing bound-below-threshold criterion machinery).
"""
from __future__ import annotations

from polymer_grammar import (
    FIREWALL_STATEMENT,
    CategoricalLeaf,
    Claim,
    MorphospaceState,
    PatternRef,
    PendingReason,
    Status,
    StrengthVector,
    get_pattern,
    morphospace_state,
    morphospace_state_of,
)

_POS = PatternRef(id="adjusted_effect", version="v1")
_NEG = PatternRef(id="bounded_absence", version="v1")


def _sv(severity: float) -> StrengthVector:
    # only .severity is read by morphospace_state; fill the other axes validly
    return StrengthVector(
        magnitude=severity, certainty=severity, evidence_against_null=severity,
        severity=severity, world_contact=severity, explanatory_virtue=severity,
    )


def _claim(cid, pattern, status, *, severity=None, pending_reason=None):
    return Claim(
        id=cid, title=cid, pattern=pattern,
        leaves=(CategoricalLeaf(ontology_term=f"t-{cid}"),),
        status=status, pending_reason=pending_reason,
        strength=(_sv(severity) if severity is not None else None),
    )


def test_asserts_absence_defaults_false_and_bounded_absence_is_true():
    assert get_pattern("adjusted_effect", "v1").asserts_absence is False
    assert get_pattern("bounded_absence", "v1").asserts_absence is True


def test_licensed_presence_is_occupied():
    c = _claim("p", _POS, Status.LICENSED, severity=0.9)
    assert morphospace_state(c, asserts_absence=False) is MorphospaceState.OCCUPIED


def test_licensed_severe_negative_is_forbidden():
    c = _claim("n", _NEG, Status.LICENSED, severity=0.9)
    assert morphospace_state(c, asserts_absence=True, severity_floor=0.5) is MorphospaceState.FORBIDDEN
    assert morphospace_state_of(c, severity_floor=0.5) is MorphospaceState.FORBIDDEN  # resolves via registry


def test_licensed_weak_negative_below_floor_is_not_forbidden():
    c = _claim("weak", _NEG, Status.LICENSED, severity=0.1)
    # a licensed negative that isn't severe enough is NOT a forbidden region (it's OTHER, not FORBIDDEN)
    assert morphospace_state(c, asserts_absence=True, severity_floor=0.5) is MorphospaceState.OTHER


def test_pending_untested_is_unobserved_not_forbidden():
    c = _claim("u", _NEG, Status.PENDING, pending_reason=PendingReason.UNTESTED)
    assert morphospace_state_of(c) is MorphospaceState.UNOBSERVED  # nobody looked != forbidden


def test_firewall_statement_is_licensing_not_meaning():
    assert "not" in FIREWALL_STATEMENT.lower() and "impossibility" in FIREWALL_STATEMENT.lower()
    assert "licensing status" in FIREWALL_STATEMENT.lower()
