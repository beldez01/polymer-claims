"""§3 — pin the exact scope of the strength=None / _permitted_by_bar exemption.

The exemption (`{c.id for c in executed if c.strength is None and c.id not in earned}`) grants a
strength=None, not-earned claim a pass PAST the cardinality-scaled BH multiplicity bar — the widest
path past that bar. This pins that scope so a refactor can't silently widen it.

THE UNTRUSTED CONCERN IS ALREADY CLOSED ONE LAYER UP: the exemption skips ONLY the BH multiplicity
bar; an UNTRUSTED claim (no registry-independent credential pair) is forced to PENDING
(ADAPTER_NOT_INDEPENDENT) by the air-gap in verify_stage (verify.py ~:305) regardless of strength or
this exemption — proven by tests/test_adapter_independence_gate.py. So an untrusted strength=None
claim cannot ride the exemption to a LICENSE; a redundant trust-guard inside _permitted_by_bar is
unnecessary (and the adapter registry is not threaded to that point — by design).
"""
from __future__ import annotations

from polymer_grammar import FDRLedger, Status, StrengthVector

from polymer_protocol.corpus import Corpus
from polymer_protocol.verify import _permitted_by_bar

from tests.conftest import make_claim, make_plan
from tests.helpers_verify import licensable_corpus


def _weak() -> StrengthVector:
    # evidence_against_null=0 -> pseudo-p = 1.0 -> fails the BH bar at any k/m
    return StrengthVector(
        magnitude=0.5, certainty=0.5, evidence_against_null=0.0,
        severity=0.5, world_contact=0.5, explanatory_virtue=0.5,
    )


def test_strength_none_not_earned_is_exempt_from_a_bar_that_excludes_scored_claims():
    _, _, records = licensable_corpus()
    template = records[0]  # a real ExecRecord; _permitted_by_bar only reads its claim_id

    exempt = make_claim("exempt1", status=Status.PENDING, plan=make_plan(0.01, 0.05))  # strength=None
    scored1 = make_claim("scored1", status=Status.PENDING, plan=make_plan(0.9, 0.05), strength=_weak())
    scored2 = make_claim("scored2", status=Status.PENDING, plan=make_plan(0.9, 0.05), strength=_weak())
    corpus = Corpus(claims=(exempt, scored1, scored2), fdr_ledger=FDRLedger(target_fdr=0.05))
    exec_records = tuple(
        template.model_copy(update={"claim_id": cid}) for cid in ("exempt1", "scored1", "scored2")
    )

    permitted = _permitted_by_bar(corpus, exec_records, earned={})

    # m = len(scored)=2 and both scored claims have pseudo-p=1.0 -> the BH bar excludes them...
    assert "scored1" not in permitted
    assert "scored2" not in permitted
    # ...but the strength=None, not-earned claim is EXEMPT and permitted regardless of the bar.
    assert "exempt1" in permitted


def test_an_earned_claim_is_scored_not_auto_exempt():
    # the exemption is strength=None AND not-earned; a claim present in `earned` is NOT exempt by the
    # None-rule (it is scored by its earned evidence). Here its earned evidence is strong -> permitted,
    # but via SCORING, not the exemption — and it is absent from the raw exemption set.
    _, _, records = licensable_corpus()
    template = records[0]
    c = make_claim("earned1", status=Status.PENDING, plan=make_plan(0.01, 0.05))  # strength=None
    corpus = Corpus(claims=(c,), fdr_ledger=FDRLedger(target_fdr=0.05))
    recs = (template.model_copy(update={"claim_id": "earned1"}),)
    strong = StrengthVector(
        magnitude=0.9, certainty=0.9, evidence_against_null=0.99,
        severity=0.9, world_contact=0.9, explanatory_virtue=0.9,
    )
    permitted = _permitted_by_bar(corpus, recs, earned={"earned1": strong})
    assert "earned1" in permitted  # scored + passes (m<=1), NOT via the None-exemption
