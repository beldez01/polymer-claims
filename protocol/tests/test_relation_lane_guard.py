"""Task 7: `is_relation` lane guard — relation claims never enter SELECT/EXECUTE/FDR.

Relation claims are built CONJECTURED with evaluation_plan=None, so `_is_candidate`
already excludes them incidentally (it requires PENDING + a plan). That incidental
exclusion is fragile: if a future slice changes a relation claim's status or gives it
a plan, the incidental path stops protecting the lane. The explicit `is_relation(c)`
guard in `_is_candidate` is defense-in-depth so "nothing charges FDR for a relation"
(spec §9) is mechanical, not an accident of today's construction defaults.
"""
from __future__ import annotations

from polymer_grammar import (
    Claim,
    FDRLedger,
    PendingReason,
    RelationKind,
    Status,
    Tier,
    is_relation,
    make_relation_claim,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.cycle import run_cycle
from polymer_protocol.select import _is_candidate

from .conftest import make_claim, make_plan


def _pending_relation_with_plan(rel: Claim) -> Claim:
    """Force `rel` into a PENDING + planned state — i.e. the exact shape `_is_candidate`
    would otherwise treat as a candidate — to prove the `is_relation` guard fires on its
    own, not merely by riding along with the incidental PENDING/plan exclusion.
    model_copy() alone skips Claim's validators, so round-trip through model_validate."""
    return Claim.model_validate(
        rel.model_copy(
            update={
                "status": Status.PENDING,
                "pending_reason": PendingReason.UNTESTED,
                "evaluation_plan": make_plan(0.01, 0.05),
            }
        ).model_dump()
    )


def _relation_claim(cid: str = "r") -> Claim:
    return make_relation_claim(
        cid, ["a"], ["b"], Tier.BIOLOGICAL, RelationKind.TENSION, -0.6, rationale="x",
    )


def test_is_candidate_rejects_relation_even_when_pending_and_planned():
    rel = _pending_relation_with_plan(_relation_claim())
    # sanity: this claim WOULD pass the incidental PENDING+plan check on its own —
    # the guard has to be the thing doing the excluding, not the incidental path.
    assert rel.status == Status.PENDING and rel.evaluation_plan is not None
    assert is_relation(rel)
    assert _is_candidate(rel) is False


def test_relation_never_selected_executed_or_charged_to_fdr(empty_ledger, ctx, adapters):
    a = make_claim("a", status=Status.PENDING, plan=make_plan(0.01, 0.05))
    rel = _relation_claim("r")
    corpus = Corpus(claims=(a, rel), fdr_ledger=empty_ledger)

    # Offer evidence for BOTH claims. If the relation claim ever slipped into SELECT/EXECUTE,
    # this evidence would let VERIFY charge it an FDR test; the guard must make that impossible
    # regardless of what evidence is available.
    result = run_cycle(corpus, adapters, ctx, evidence={"a": 0.01, "r": 0.01})

    rel_ids = {c.id for c in corpus.claims if is_relation(c)}
    assert rel_ids == {"r"}
    assert not (rel_ids & {t.claim_id for t in result.corpus.fdr_ledger.tests})

    out_rel = result.corpus.by_id()["r"]
    assert out_rel.status == rel.status  # unchanged: never executed, never touched by VERIFY
    assert out_rel == rel

    selected_ids = {d.claim_id for d in result.selection.decisions if d.selected}
    assert "r" not in selected_ids
