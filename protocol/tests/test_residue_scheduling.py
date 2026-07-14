"""neg-whisper ③ — residue budget for the PENDING graveyard.

The scheduler earns a RESIDUE_REEXAM action for PENDING claims with dependents when the residue
weight is > 0; at the default weight 0 it is byte-identical (no such action ever proposed — also
covered by the unchanged existing economics suite).
"""
from __future__ import annotations

from polymer_grammar import EquivalenceClaim, FDRLedger, PendingReason, Status

from polymer_protocol import ActionKind
from polymer_protocol.corpus import Corpus
from polymer_protocol.economics import (
    SchedulerConfig,
    SchedulerState,
    SchedulerWeights,
    next_action,
)


def _residue_corpus(make_quantity_claim):
    # D = a duhem_underdetermined PENDING claim with 2 dependents (equivalence edges to x, y).
    # U = an isolated untested PENDING claim (no edges).
    d = make_quantity_claim("D", 1.0, Status.PENDING, pending_reason=PendingReason.DUHEM_UNDERDETERMINED)
    u = make_quantity_claim("U", 1.0, Status.PENDING, pending_reason=PendingReason.UNTESTED)
    x = make_quantity_claim("x", 1.0, Status.LICENSED)
    y = make_quantity_claim("y", 1.0, Status.LICENSED)
    equivs = (
        EquivalenceClaim(id="e1", left="D", right="x", severity=0.5, status=Status.LICENSED),
        EquivalenceClaim(id="e2", left="D", right="y", severity=0.5, status=Status.LICENSED),
    )
    # PENDING claims here carry no evaluation_plan -> NOT selectable -> no RUN_CYCLE competes, so the
    # residue action is observable as the winner when enabled.
    return Corpus(claims=(d, u, x, y), equivalences=equivs, fdr_ledger=FDRLedger(target_fdr=0.05))


def test_residue_off_by_default_no_reexam_action(make_quantity_claim):
    state = SchedulerState(corpus=_residue_corpus(make_quantity_claim))
    action = next_action(state, budget=100.0)  # default weights: residue=0.0
    assert action is None or action.kind is not ActionKind.RESIDUE_REEXAM


def test_residue_on_schedules_high_dependency_pending_ahead_of_isolated(make_quantity_claim):
    state = SchedulerState(corpus=_residue_corpus(make_quantity_claim))
    cfg = SchedulerConfig(weights=SchedulerWeights(residue=1.0))
    action = next_action(state, budget=100.0, config=cfg)
    assert action is not None
    assert action.kind is ActionKind.RESIDUE_REEXAM
    assert "D" in action.rationale          # the duhem claim with dependents...
    assert "U" not in action.rationale      # ...not the isolated untested one
    assert action.estimated_value == 2.0    # residue weight 1.0 * degree 2


def test_isolated_untested_only_earns_no_reexam(make_quantity_claim):
    u = make_quantity_claim("U", 1.0, Status.PENDING, pending_reason=PendingReason.UNTESTED)
    corpus = Corpus(claims=(u,), fdr_ledger=FDRLedger(target_fdr=0.05))
    cfg = SchedulerConfig(weights=SchedulerWeights(residue=1.0))
    action = next_action(SchedulerState(corpus=corpus), budget=100.0, config=cfg)
    # zero dependents -> residue-value 0 -> no re-exam earned (a budget, not a mandate)
    assert action is None or action.kind is not ActionKind.RESIDUE_REEXAM
