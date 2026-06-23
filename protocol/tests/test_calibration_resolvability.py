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
