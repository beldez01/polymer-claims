"""test_verify_multiplicity_withheld.py — BH-bar-withheld claims get an honest pending_reason.

TE-note CORRECTION gap (i): an evaluated e-LOND discovery held back ONLY by the cardinality-scaled
BH multiplicity bar used to fall through and keep its stale incoming UNTESTED — misreporting a claim
that was in fact tested. It must now carry MULTIPLICITY_WITHHELD. Status (the gate decision) is
unchanged; this is a reporting fix. A claim that clears the bar still licenses.
"""
from __future__ import annotations

from polymer_grammar import (
    FDRLedger,
    IdentityAdapter,
    MaterializationContext,
    PendingReason,
    ReferenceAdapter,
    Status,
    StrengthVector,
)

from polymer_protocol.commit import commit
from polymer_protocol.corpus import Corpus, CycleScaffolding
from polymer_protocol.execute import execute_ground
from polymer_protocol.verify import verify_stage

from tests.conftest import make_claim, make_plan

_ADAPTERS = (IdentityAdapter(), ReferenceAdapter(identity="reference"))
_CTX = MaterializationContext(id="M1", api_version="v1", data_version="d1")


def _sv(evidence_against_null: float) -> StrengthVector:
    return StrengthVector(
        magnitude=0.8, certainty=0.8, evidence_against_null=evidence_against_null,
        severity=0.8, world_contact=0.8, explanatory_virtue=0.8,
    )


def _run_two_claim_bar():
    """Two satisfied+grounded claims scored by the BH bar: 'pass' (near-zero pseudo-p) clears it,
    'hold' (high pseudo-p) is withheld. Returns the verified corpus by-id map."""
    # pseudo-p = 1 - evidence_against_null. pass -> 0.001 (clears); hold -> 0.30 (fails k/m*Q bar).
    c_pass = make_claim("pass", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv(0.999))
    c_hold = make_claim("hold", status=Status.PENDING, plan=make_plan(0.01, 0.05), strength=_sv(0.70))
    corpus = commit(Corpus(claims=(c_pass, c_hold), fdr_ledger=FDRLedger(target_fdr=0.05)))
    corpus, records, _ = execute_ground(corpus, _ADAPTERS, _CTX)
    scaffolding = CycleScaffolding(grounded_extension=("pass", "hold"))
    out = verify_stage(corpus, scaffolding, records)
    return out.by_id()


def test_bh_withheld_claim_is_labeled_multiplicity_withheld_not_untested():
    by_id = _run_two_claim_bar()
    hold = by_id["hold"]
    # Withheld only by the multiplicity bar → PENDING, but honestly labeled (NOT the stale UNTESTED).
    assert hold.status == Status.PENDING
    assert hold.pending_reason == PendingReason.MULTIPLICITY_WITHHELD
    assert hold.pending_reason != PendingReason.UNTESTED
    assert hold.licensing is None


def test_claim_that_clears_the_bar_still_licenses():
    by_id = _run_two_claim_bar()
    passed = by_id["pass"]
    # The gate decision is unaffected by the reporting fix: the bar-clearing claim licenses.
    assert passed.status == Status.LICENSED
    assert passed.licensing is not None
