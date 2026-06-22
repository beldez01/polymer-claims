"""End-to-end calibration harness tests: synthetic cohorts through the REAL gate -> DEFINITIONAL records.

N_BATCHES, CAL_FDR_TOLERANCE, and K are PINNED a-priori constants. Do NOT raise them to make a
failing test pass -- a persistent breach is a real miscalibration signal to investigate.
"""
import pytest

pytest.importorskip("numpy")

# ---------------------------------------------------------------------------
# Pinned module-level constants (fixed BEFORE running)
# ---------------------------------------------------------------------------
N_BATCHES = 12          # spec N~12
CAL_FDR_TOLERANCE = 0.02  # absolute margin on mean per-batch FDP.
# Rationale (pinned a priori): a calibrated e-LOND gate has E[FDP] <= q = 0.05. The Monte-Carlo
# standard error of the mean of N=12 per-batch FDPs (each a proportion near q) is ~sqrt(q(1-q)/m)/sqrt(N)
# for batch licensed-count m~tens, i.e. on the order of 0.01-0.015; 0.02 is ~1.5 SE of slack. This
# absorbs finite-N noise WITHOUT admitting a gate whose mean FDP is materially above q (e.g. 0.10
# would fail). It is fixed here and MUST NOT be raised to make a red test pass -- a persistent breach
# is a real miscalibration finding to investigate (Phase A: "honest failure is an acceptable outcome").

from polymer_protocol.calibration import (  # noqa: E402
    GeneratingModelParams,
    ResolutionKind,
    ResolutionVerdict,
    calibration_summary,
)
from polymer_claims.calibration_harness import run_batch, run_calibration  # noqa: E402


def _model(**kw):
    base = dict(
        model_id="m1",
        n_per_group=30,
        n_probes_per_region=6,
        effect_size=0.30,
        dispersion=25.0,
        fraction_true=0.5,
        tau=0.10,
        target_fdr=0.05,
        n_generated=8,
        seed_set=(0,),
    )
    base.update(kw)
    return GeneratingModelParams(**base)


# ---------------------------------------------------------------------------
# Step 1 tests (basic correctness + determinism)
# ---------------------------------------------------------------------------

def test_all_true_batch_has_no_false_licenses():
    recs = run_batch(model=_model(fraction_true=1.0, n_generated=8), batch_id="t", seed=0)
    # every record is DEFINITIONAL; a false license would be verdict=FAILED on a true region -> impossible
    assert all(r.resolution_kind == ResolutionKind.DEFINITIONAL for r in recs)
    assert all(r.verdict != ResolutionVerdict.FAILED for r in recs)


def test_records_are_deterministic_for_fixed_seed():
    a = run_batch(model=_model(), batch_id="b", seed=7)
    b = run_batch(model=_model(), batch_id="b", seed=7)
    assert [(r.subject_claim_id, r.verdict) for r in a] == [(r.subject_claim_id, r.verdict) for r in b]


# ---------------------------------------------------------------------------
# Step 6 tests (FDR calibration envelope -- pinned constants)
# ---------------------------------------------------------------------------

def test_mixed_batch_realized_fdr_consistent_with_target():
    model = _model(fraction_true=0.6, n_generated=40, effect_size=0.30, n_per_group=40)
    ledger = run_calibration(model=model, n_batches=N_BATCHES, base_seed=100)
    rep = calibration_summary(ledger, target_q=model.target_fdr)
    assert rep.definitional.realized_rate is not None
    # deterministic (fixed seeds). Pass-rule (spec §8 bar 2): mean per-batch FDP <= q + pinned tolerance.
    assert rep.definitional.realized_rate <= model.target_fdr + CAL_FDR_TOLERANCE, (
        f"realized FDR {rep.definitional.realized_rate:.4f} > q={model.target_fdr} + "
        f"tolerance={CAL_FDR_TOLERANCE} -- investigate gate miscalibration"
    )


def test_all_null_control_licenses_are_bounded():
    # all-null: every license is false. This is a CONTROL of per-comparison false-positive behavior,
    # NOT the headline FDR. Fixed seed -> deterministic count -> assert a conservative pinned bound.
    model = _model(fraction_true=0.0, n_generated=40, n_per_group=40)
    recs = run_batch(model=model, batch_id="null", seed=200)
    # K: a conservative a-priori bound. Under H0 the per-claim type-I rate is governed by the e-LOND
    # threshold; for 40 null regions at q=0.05 we expect very few licenses. K is pinned, not tuned.
    K = 4
    assert len(recs) <= K, (
        f"all-null licensed {len(recs)} > pinned bound {K} -- investigate the gate"
    )
