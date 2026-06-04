from __future__ import annotations

from polymer_grammar import (
    LicenseRoute,
    Licensing,
    MaterializationContext,
    RivalSetClosure,
    Satisfaction,
    SatisfactionVerdict,
    Status,
)

from polymer_protocol.corpus import Corpus
from polymer_protocol.drift import drift_pass
from tests.conftest import make_claim, make_plan


def _mat(mid: str, api: str, data: str) -> MaterializationContext:
    return MaterializationContext(id=mid, api_version=api, data_version=data)


def _lic(*mats: MaterializationContext) -> Licensing:
    """A valid Licensing record over the given materializations (all SATISFIED)."""
    sats = tuple(
        Satisfaction(verdict=SatisfactionVerdict.SATISFIED, materialization=m) for m in mats
    )
    route = LicenseRoute.REPLICATION if len({m.id for m in mats}) >= 2 else LicenseRoute.SEVERE_TEST
    return Licensing(
        route=route,
        rival_set_closure=RivalSetClosure.OPEN_ACKNOWLEDGED,
        rivals_considered=(),
        satisfactions=sats,
    )


def _corpus(empty_ledger, *claims) -> Corpus:
    return Corpus(claims=tuple(claims), fdr_ledger=empty_ledger)


_CURRENT = _mat("now", "v1", "d1")


def test_stale_licensed_claim_is_flagged(empty_ledger):
    c = make_claim("c", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    corpus = _corpus(empty_ledger, c)
    out, rec = drift_pass(corpus, current=_CURRENT)
    assert [f.claim_id for f in rec.drifted] == ["c"]
    assert rec.examined == 1
    assert rec.drifted[0].licensed_versions == (("v0", "d0"),)


def test_fresh_licensed_claim_is_not_flagged(empty_ledger):
    c = make_claim("c", Status.LICENSED, licensing=_lic(_mat("M1", "v1", "d1")))
    out, rec = drift_pass(_corpus(empty_ledger, c), current=_CURRENT)
    assert rec.drifted == ()
    assert rec.examined == 1


def test_replication_fresh_if_any_satisfaction_matches(empty_ledger):
    # M_old is stale but M_now matches current -> fresh (any-match rule)
    c = make_claim(
        "c", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0"), _mat("M1", "v1", "d1"))
    )
    out, rec = drift_pass(_corpus(empty_ledger, c), current=_CURRENT)
    assert rec.drifted == ()


def test_replication_drifted_if_no_satisfaction_matches(empty_ledger):
    c = make_claim(
        "c", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0"), _mat("M9", "v9", "d9"))
    )
    out, rec = drift_pass(_corpus(empty_ledger, c), current=_CURRENT)
    assert [f.claim_id for f in rec.drifted] == ["c"]
    assert rec.drifted[0].licensed_versions == (("v0", "d0"), ("v9", "d9"))


def test_non_licensed_claims_are_never_scanned(empty_ledger):
    a = make_claim("a", Status.CONJECTURED)
    b = make_claim("b", Status.PENDING)
    c = make_claim("c", Status.REJECTED)
    out, rec = drift_pass(_corpus(empty_ledger, a, b, c), current=_CURRENT)
    assert rec.examined == 0
    assert rec.drifted == ()


def test_re_executable_reflects_evaluation_plan(empty_ledger):
    planned = make_claim(
        "p", Status.LICENSED, plan=make_plan(0.01, 0.05), licensing=_lic(_mat("M0", "v0", "d0"))
    )
    planless = make_claim("q", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    out, rec = drift_pass(_corpus(empty_ledger, planned, planless), current=_CURRENT)
    by_id = {f.claim_id: f.re_executable for f in rec.drifted}
    assert by_id == {"p": True, "q": False}


def test_returned_corpus_is_the_same_object(empty_ledger):
    c = make_claim("c", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    corpus = _corpus(empty_ledger, c)
    out, rec = drift_pass(corpus, current=_CURRENT)
    assert out is corpus  # flag-only: never mutates the corpus


def test_licensed_without_licensing_block_is_counted_but_not_flagged(empty_ledger):
    # A LICENSED claim may carry licensing=None (the validator only forbids licensing on
    # non-LICENSED, it does not require it). Drift can't be assessed -> examined but not drifted.
    c = make_claim("c", Status.LICENSED)
    out, rec = drift_pass(_corpus(empty_ledger, c), current=_CURRENT)
    assert rec.examined == 1
    assert rec.drifted == ()


def test_drift_pass_is_deterministic(empty_ledger):
    c2 = make_claim("c2", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    c1 = make_claim("c1", Status.LICENSED, licensing=_lic(_mat("M0", "v0", "d0")))
    corpus = _corpus(empty_ledger, c2, c1)
    _, r1 = drift_pass(corpus, current=_CURRENT)
    _, r2 = drift_pass(corpus, current=_CURRENT)
    assert r1 == r2
    assert [f.claim_id for f in r1.drifted] == ["c1", "c2"]  # sorted by claim_id
