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


def test_anchored_resolutions_sets_exposure_start_cycle():
    # the exposure clock (the cycle the epoch was licensed) is threaded via PressureContext
    prev = _corpus(licensed_claim("c1"))
    curr = _corpus(rejected_claim("c1", RejectionReason.DEFEAT_GROUNDED_OUT))
    pc = PressureContext(
        epoch={"c1": 0}, cause={"c1": PressureKind.DEFEAT}, exposure_start={"c1": 4}
    )
    (rec,) = anchored_resolutions(prev, curr, cycle=10, pressure=pc)
    assert rec.exposure_start_cycle == 4  # survival time would be observed(10) - start(4) = 6


def test_anchored_resolutions_are_deterministically_ordered():
    # The impure caller builds `cause` from a set comprehension, so its key/insertion
    # order is PYTHONHASHSEED-dependent. The emitted records flow into the JSONL ledger
    # and the signed certificate digest, so their order MUST be deterministic regardless
    # of how `cause` was iterated. Insert the cause keys deliberately out of order.
    ids = ["c3", "c1", "c2"]
    prev = _corpus(*[licensed_claim(c) for c in ids])
    curr = _corpus(*[licensed_claim(c) for c in ids])
    pc = PressureContext(
        epoch={c: 0 for c in ids},
        cause={c: PressureKind.DRIFT for c in ids},  # inserted c3, c1, c2
        survived=frozenset(ids),
    )
    got = [r.subject_claim_id for r in anchored_resolutions(prev, curr, cycle=1, pressure=pc)]
    assert got == sorted(got), f"records not deterministically ordered: {got}"
    assert got == ["c1", "c2", "c3"]
