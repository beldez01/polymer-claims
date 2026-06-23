import math
from polymer_protocol.calibration import (
    ResolutionRecord, ResolutionKind, CalibrationTarget, ResolutionVerdict, PressureKind,
    CalibrationLedger, calibration_summary,
)

D, A = ResolutionKind.DEFINITIONAL, ResolutionKind.ANCHORED
FDR, WS = CalibrationTarget.REALIZED_FDR, CalibrationTarget.WARRANT_SURVIVAL
UP, FL, UN, SUP = (ResolutionVerdict.UPHELD, ResolutionVerdict.FAILED,
                   ResolutionVerdict.UNRESOLVED, ResolutionVerdict.SUPERSEDED)


def _d(cid, batch, truth, q=0.05):
    return ResolutionRecord(
        subject_claim_id=cid, license_epoch=0, resolution_kind=D, calibration_target=FDR,
        verdict=UP if truth else FL, stated_q=q, observed_at_cycle=0,
        constructed_truth=truth, model_id="m", batch_id=batch,
    )


def _a(cid, verdict, cyc):
    return ResolutionRecord(
        subject_claim_id=cid, license_epoch=0, resolution_kind=A, calibration_target=WS,
        verdict=verdict, stated_q=0.05, observed_at_cycle=cyc, pressure_kind=PressureKind.DEFEAT,
    )


def test_definitional_mean_fdp_differs_from_pooled_on_uneven_batches():
    # batch A: 1 licensed, 1 false -> FDP 1.0 ; batch B: 9 licensed, 1 false -> FDP 1/9
    recs = [_d("a1", "A", False)]
    recs += [_d(f"b{i}", "B", i != 0) for i in range(9)]  # b0 false, b1..b8 true
    rep = calibration_summary(CalibrationLedger(records=tuple(recs)), target_q=0.05)
    # mean per-batch FDP = (1.0 + 1/9)/2 = 0.5555..., pooled = 2/10 = 0.2 -> they MUST differ
    assert math.isclose(rep.definitional.realized_rate, (1.0 + 1 / 9) / 2, rel_tol=1e-9)
    assert math.isclose(rep.definitional.pooled_rate, 0.2, rel_tol=1e-9)
    assert rep.definitional.n_batches == 2
    assert rep.definitional.n_total == 10 and rep.definitional.n_failed == 2


def test_report_filters_definitional_by_target_q():
    recs = [_d("x", "A", False, q=0.05), _d("y", "A", False, q=0.10)]
    rep = calibration_summary(CalibrationLedger(records=tuple(recs)), target_q=0.05)
    assert rep.definitional.n_total == 1  # only the stated_q==0.05 record


def test_anchored_excludes_unresolved_and_superseded_from_denominator():
    recs = [_a("u1", UN, 1), _a("f1", FL, 2), _a("p1", UP, 3),
            ResolutionRecord(subject_claim_id="s1", license_epoch=0, resolution_kind=A,
                             calibration_target=WS, verdict=SUP, stated_q=0.05,
                             observed_at_cycle=4, pressure_kind=PressureKind.DRIFT)]
    rep = calibration_summary(CalibrationLedger(records=tuple(recs)), target_q=0.05)
    assert rep.anchored.n_total == 2          # failed + upheld only
    assert rep.anchored.n_failed == 1
    assert rep.anchored.n_unresolved == 1
    assert rep.anchored.n_superseded == 1
    assert math.isclose(rep.anchored.realized_rate, 0.5, rel_tol=1e-9)
    assert rep.observation_span_cycles == 3   # max(4) - min(1)


def test_empty_tier_has_none_rate():
    rep = calibration_summary(CalibrationLedger(records=()), target_q=0.05)
    assert rep.definitional.realized_rate is None
    assert rep.attested.n_total == 0


def _a_q(cid, verdict, cyc, q):
    """ANCHORED record with an explicit stated_q."""
    return ResolutionRecord(
        subject_claim_id=cid, license_epoch=0, resolution_kind=A, calibration_target=WS,
        verdict=verdict, stated_q=q, observed_at_cycle=cyc, pressure_kind=PressureKind.DEFEAT,
    )


def test_anchored_stat_scoped_to_target_q():
    """A report for one target_q must NOT count anchored records for a different q."""
    recs = [
        _a_q("c1", FL, 1, 0.05),
        _a_q("c2", UP, 2, 0.05),
        _a_q("c3", FL, 3, 0.10),   # different q — must be excluded from target_q=0.05 report
        _a_q("c4", UP, 4, 0.10),   # different q — must be excluded
    ]
    rep = calibration_summary(CalibrationLedger(records=tuple(recs)), target_q=0.05)
    # Only the two q=0.05 records count
    assert rep.anchored.n_total == 2
    assert rep.anchored.n_failed == 1
    # observation_span_cycles must also reflect only q=0.05 records (cycles 1 and 2)
    assert rep.observation_span_cycles == 1   # max(2) - min(1)


def test_single_batch_ci_is_none():
    """A single-batch definitional stat cannot yield a meaningful 95% CI."""
    recs = [_d("a1", "batch-only", True), _d("a2", "batch-only", False)]
    rep = calibration_summary(CalibrationLedger(records=tuple(recs)), target_q=0.05)
    assert rep.definitional.n_batches == 1
    assert rep.definitional.ci_low is None
    assert rep.definitional.ci_high is None
    assert rep.definitional.ci_method is None


def _a_exp(cid, verdict, observed, start):
    return ResolutionRecord(
        subject_claim_id=cid, license_epoch=0, resolution_kind=A, calibration_target=WS,
        verdict=verdict, stated_q=0.05, observed_at_cycle=observed,
        pressure_kind=PressureKind.DEFEAT, exposure_start_cycle=start,
    )


def test_anchored_hazard_rate_is_failures_per_exposure_cycle():
    # 2 failed (exposure 10 each) + 1 upheld (exposure 30) → hazard = 2 / (10+10+30) = 0.04
    recs = [
        _a_exp("f1", FL, observed=10, start=0),
        _a_exp("f2", FL, observed=20, start=10),
        _a_exp("u1", UP, observed=30, start=0),
    ]
    rep = calibration_summary(CalibrationLedger(records=tuple(recs)), target_q=0.05)
    assert rep.anchored.total_exposure_cycles == 50
    assert math.isclose(rep.anchored.hazard_rate, 2 / 50, rel_tol=1e-9)


def test_anchored_hazard_none_without_exposure():
    # records lacking exposure_start_cycle (old ledgers) → no hazard, but the rate still computes
    recs = [_a("f1", FL, 5), _a("u1", UP, 9)]
    rep = calibration_summary(CalibrationLedger(records=tuple(recs)), target_q=0.05)
    assert rep.anchored.hazard_rate is None
    assert rep.anchored.realized_rate == 0.5  # 1 failed / 2 resolved still works
