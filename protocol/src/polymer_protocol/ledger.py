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
HIGH_EIG = 0.5


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
