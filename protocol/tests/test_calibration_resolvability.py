import pytest
from polymer_protocol.calibration import (
    ResolutionRecord, ResolutionKind, CalibrationTarget, ResolutionVerdict, Resolvability,
)


def _attested(**kw):
    base = dict(
        subject_claim_id="c1", license_epoch=0,
        resolution_kind=ResolutionKind.ATTESTED,
        calibration_target=CalibrationTarget.EXTERNAL_DISAGREEMENT,
        verdict=ResolutionVerdict.UPHELD, stated_q=0.05, observed_at_cycle=0,
        attestation_ref="doi:10.1056/x", source_claim_id="attest-abc",
    )
    base.update(kw)
    return ResolutionRecord(**base)


def _definitional(**kw):
    base = dict(
        subject_claim_id="c1", license_epoch=0,
        resolution_kind=ResolutionKind.DEFINITIONAL,
        calibration_target=CalibrationTarget.REALIZED_FDR,
        verdict=ResolutionVerdict.UPHELD, stated_q=0.05, observed_at_cycle=0,
        constructed_truth=True, model_id="m1", batch_id="b1",
    )
    base.update(kw)
    return ResolutionRecord(**base)


def test_resolvability_allowed_on_attested():
    r = _attested(resolvability=Resolvability.RESOLVABLE)
    assert r.resolvability is Resolvability.RESOLVABLE


def test_resolvability_defaults_none():
    assert _attested().resolvability is None


def test_resolvability_rejected_on_non_attested():
    with pytest.raises(ValueError, match="resolvability"):
        _definitional(resolvability=Resolvability.RESOLVABLE)


from polymer_protocol.calibration import resolvability_prior


def _claim(plan):
    # Minimal claim via the protocol test conftest builder.
    from tests.conftest import make_claim, make_plan
    return make_claim("subj", plan=plan)


def test_prior_resolvable_when_plan_present():
    from tests.conftest import make_plan
    assert resolvability_prior(_claim(make_plan(0.01, 0.05))) is Resolvability.RESOLVABLE


def test_prior_unresolvable_when_plan_absent():
    assert resolvability_prior(_claim(None)) is Resolvability.UNRESOLVABLE


from polymer_protocol.calibration import CalibrationLedger, calibration_summary


def test_attested_stat_counts_resolvability_split_and_q():
    recs = (
        _attested(subject_claim_id="a", verdict=ResolutionVerdict.FAILED,
                  resolvability=Resolvability.RESOLVABLE, source_claim_id="attest-a"),
        _attested(subject_claim_id="b", verdict=ResolutionVerdict.UPHELD,
                  resolvability=Resolvability.RESOLVABLE, source_claim_id="attest-b"),
        _attested(subject_claim_id="c", verdict=ResolutionVerdict.UPHELD,
                  resolvability=Resolvability.UNRESOLVABLE, source_claim_id="attest-c"),
        # an UNRESOLVED record must be EXCLUDED from both q_attested and the resolvability split:
        _attested(subject_claim_id="d", verdict=ResolutionVerdict.UNRESOLVED,
                  resolvability=Resolvability.RESOLVABLE, source_claim_id="attest-d"),
    )
    rep = calibration_summary(CalibrationLedger(records=recs), target_q=0.05)
    at = rep.attested
    assert at.n_total == 3 and at.n_failed == 1   # UNRESOLVED 'd' excluded from the denominator
    assert at.realized_rate == 1 / 3            # q_attested = failed/(failed+upheld), unchanged
    assert at.n_resolvable == 2                 # 'd' NOT counted despite resolvability=RESOLVABLE
    assert at.n_unresolvable == 1
    assert at.n_resolvable + at.n_unresolvable == at.n_total  # split matches the q denominator


def test_attested_never_feeds_headline_q():
    r = _attested(resolvability=Resolvability.RESOLVABLE)
    assert r.feeds_headline_q is False
