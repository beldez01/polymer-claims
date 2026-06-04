"""SelectionLedger — the threaded cross-cycle pursuit state for SELECT #3b.

Protocol pursuit-state, NOT grammar knowledge: passed into run_cycle and returned on
CycleResult (Corpus stays grammar-IR-only / 4 collections). Holds per-claim accumulated
execution outcomes (for accumulating belief) and per-operator surprise-grounding credit
(for the Goodhart guard). Pure, deterministic. Spec §2, §4.
"""
from __future__ import annotations

from pydantic import Field, model_validator

from polymer_grammar import Claim, GenerationMode

from .base import _Model

CREDIT_A0 = 1.0
HIGH_EIG = 0.2  # calibrated to the EIG scale (max ~0.278 at the uniform Beta(1,1) prior)


class ClaimOutcome(_Model):
    claim_id: str
    successes: int = Field(default=0, ge=0)
    failures: int = Field(default=0, ge=0)


class OperatorCredit(_Model):
    operator_id: str
    n_high_eig: int = Field(default=0, ge=0)
    n_grounded: int = Field(default=0, ge=0)


class SelectionLedger(_Model):
    outcomes: tuple[ClaimOutcome, ...] = ()
    credits: tuple[OperatorCredit, ...] = ()

    @model_validator(mode="after")
    def _unique_ids(self) -> "SelectionLedger":
        oids = [o.claim_id for o in self.outcomes]
        if len(oids) != len(set(oids)):
            raise ValueError("SelectionLedger outcome claim_ids must be unique")
        cids = [c.operator_id for c in self.credits]
        if len(cids) != len(set(cids)):
            raise ValueError("SelectionLedger credit operator_ids must be unique")
        return self

    def outcome(self, claim_id: str) -> ClaimOutcome | None:
        return {o.claim_id: o for o in self.outcomes}.get(claim_id)

    def credit(self, operator_id: str) -> OperatorCredit | None:
        return {c.operator_id: c for c in self.credits}.get(operator_id)


def operator_of(claim: Claim) -> str:
    """The GENERATE operator that produced a claim (#4a trace), else 'exogenous'."""
    prov = claim.provenance
    if prov is not None and prov.generated_by == GenerationMode.AGENT_GENERATED and prov.agent_id:
        return prov.agent_id
    return "exogenous"


def credit_factor(ledger: SelectionLedger, operator_id: str) -> float:
    """Optimistic smoothed grounding rate (n_grounded + A0)/(n_high_eig + A0). Untracked -> 1.0;
    systematically-failing -> toward 0. Bounded (0, 1]."""
    cr = ledger.credit(operator_id)
    if cr is None:
        return 1.0
    return (cr.n_grounded + CREDIT_A0) / (cr.n_high_eig + CREDIT_A0)


class ExecutedOutcome(_Model):
    """One claim's realized outcome this cycle, fed to update_ledger."""

    claim_id: str
    operator_id: str
    eig: float            # the raw belief-EIG at selection (for the HIGH_EIG test)
    licensed: bool
    rejected: bool


def update_ledger(ledger: SelectionLedger, outcomes: tuple[ExecutedOutcome, ...]) -> SelectionLedger:
    succ: dict[str, int] = {o.claim_id: o.successes for o in ledger.outcomes}
    fail: dict[str, int] = {o.claim_id: o.failures for o in ledger.outcomes}
    he: dict[str, int] = {c.operator_id: c.n_high_eig for c in ledger.credits}
    gr: dict[str, int] = {c.operator_id: c.n_grounded for c in ledger.credits}
    for o in outcomes:
        succ[o.claim_id] = succ.get(o.claim_id, 0) + (1 if o.licensed else 0)
        fail[o.claim_id] = fail.get(o.claim_id, 0) + (1 if o.rejected else 0)
        if o.eig >= HIGH_EIG:
            he[o.operator_id] = he.get(o.operator_id, 0) + 1
            gr[o.operator_id] = gr.get(o.operator_id, 0) + (1 if o.licensed else 0)
    new_outcomes = tuple(
        ClaimOutcome(claim_id=cid, successes=succ[cid], failures=fail.get(cid, 0))
        for cid in sorted(succ)
    )
    new_credits = tuple(
        OperatorCredit(operator_id=oid, n_high_eig=he[oid], n_grounded=gr.get(oid, 0))
        for oid in sorted(he)
    )
    return ledger.model_copy(update={"outcomes": new_outcomes, "credits": new_credits})
