from polymer_grammar import RejectionReason
from polymer_protocol.calibration import (
    anchored_resolutions, PressureContext, ResolutionVerdict, PressureKind,
)
from polymer_protocol.corpus import Corpus
from polymer_grammar.fdr import FDRLedger
# a tiny claim factory shared with other protocol tests:
from tests._calib_fixtures import licensed_claim, rejected_claim, pending_claim  # Step 3 creates this


def _corpus(*claims):
    return Corpus(claims=tuple(claims), fdr_ledger=FDRLedger(target_fdr=0.05))


def test_defeat_emits_failed():
    prev = _corpus(licensed_claim("c1"))
    curr = _corpus(rejected_claim("c1", RejectionReason.DEFEAT_GROUNDED_OUT))
    pc = PressureContext(epoch={"c1": 0}, cause={"c1": PressureKind.DEFEAT})
    (rec,) = anchored_resolutions(prev, curr, cycle=5, pressure=pc)
    assert rec.verdict == ResolutionVerdict.FAILED and rec.pressure_kind == PressureKind.DEFEAT
    assert rec.license_epoch == 0 and rec.observed_at_cycle == 5


def test_drift_no_relicense_emits_failed():
    prev = _corpus(licensed_claim("c1"))
    curr = _corpus(pending_claim("c1"))
    pc = PressureContext(epoch={"c1": 0}, cause={"c1": PressureKind.DRIFT})
    (rec,) = anchored_resolutions(prev, curr, cycle=2, pressure=pc)
    assert rec.verdict == ResolutionVerdict.FAILED and rec.pressure_kind == PressureKind.DRIFT


def test_still_licensed_no_pressure_emits_nothing():
    prev = _corpus(licensed_claim("c1"))
    curr = _corpus(licensed_claim("c1"))
    pc = PressureContext(epoch={"c1": 0}, cause={})  # no pressure event
    assert anchored_resolutions(prev, curr, cycle=9, pressure=pc) == ()


def test_drift_clean_survival_emits_upheld():
    prev = _corpus(licensed_claim("c1"))
    curr = _corpus(licensed_claim("c1"))
    pc = PressureContext(epoch={"c1": 0}, cause={"c1": PressureKind.DRIFT}, survived={"c1"})
    (rec,) = anchored_resolutions(prev, curr, cycle=4, pressure=pc)
    assert rec.verdict == ResolutionVerdict.UPHELD and rec.pressure_kind == PressureKind.DRIFT
