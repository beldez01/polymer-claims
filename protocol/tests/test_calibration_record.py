import pytest
from polymer_protocol.calibration import (
    ResolutionRecord, ResolutionKind, CalibrationTarget, ResolutionVerdict, PressureKind,
)


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


def test_feeds_headline_q_true_only_for_definitional_realized_fdr():
    assert _definitional().feeds_headline_q is True


def test_feeds_headline_q_false_for_anchored():
    r = ResolutionRecord(
        subject_claim_id="c1", license_epoch=0,
        resolution_kind=ResolutionKind.ANCHORED,
        calibration_target=CalibrationTarget.WARRANT_SURVIVAL,
        verdict=ResolutionVerdict.FAILED, stated_q=0.05, observed_at_cycle=3,
        pressure_kind=PressureKind.DEFEAT,
    )
    assert r.feeds_headline_q is False


def test_target_kind_coupling_rejected():
    with pytest.raises(ValueError, match="target"):
        _definitional(calibration_target=CalibrationTarget.WARRANT_SURVIVAL)


def test_present_only_when_kind_rejects_pressure_on_definitional():
    with pytest.raises(ValueError, match="pressure_kind"):
        _definitional(pressure_kind=PressureKind.DRIFT)


def test_definitional_requires_batch_id():
    with pytest.raises(ValueError, match="batch_id"):
        _definitional(batch_id=None)


def test_unresolved_rejected_on_definitional():
    with pytest.raises(ValueError, match="unresolved"):
        _definitional(verdict=ResolutionVerdict.UNRESOLVED)
