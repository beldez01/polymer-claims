from polymer_protocol.calibration import (
    ResolutionRecord, ResolutionKind, CalibrationTarget, ResolutionVerdict, Resolvability,
    CalibrationLedger,
)
from polymer_claims.attestation import build_certificate, render_certificate_text
from tests.attestation._fixtures import licensed_claim, licensing, corpus_with, sat, mc


def _attested(cid, verdict, resolvability):
    return ResolutionRecord(
        subject_claim_id=cid, license_epoch=0, resolution_kind=ResolutionKind.ATTESTED,
        calibration_target=CalibrationTarget.EXTERNAL_DISAGREEMENT, verdict=verdict,
        stated_q=0.05, observed_at_cycle=0, attestation_ref=f"doi:{cid}",
        source_claim_id=f"attest-{cid}", resolvability=resolvability,
    )


def test_certificate_shows_q_attested_and_resolvability_split():
    # render_certificate_text takes a Certificate; build one via build_certificate, which attaches
    # calibration_summary(ledger, target_q). Attested tier is corpus-level field calibration, so the
    # records' subjects need not be the certified claim.
    corpus = corpus_with(licensed_claim("c1", licensing(sat(mc()))))
    led = CalibrationLedger(records=(
        _attested("a", ResolutionVerdict.FAILED, Resolvability.RESOLVABLE),
        _attested("b", ResolutionVerdict.UPHELD, Resolvability.UNRESOLVABLE),
    ))
    cert = build_certificate(corpus, "c1", ledger=led, target_q=0.05)
    text = render_certificate_text(cert)
    assert "q_attested" in text
    assert "0.500" in text                      # 1 failed / 2 (failed+upheld)
    assert "1 resolvable" in text and "1 unresolvable" in text
    assert "never" in text.lower()              # disclosure present


def test_certificate_zero_attested_is_byte_identical():
    corpus = corpus_with(licensed_claim("c1", licensing(sat(mc()))))
    cert = build_certificate(corpus, "c1", ledger=CalibrationLedger(records=()), target_q=0.05)
    text = render_certificate_text(cert)
    assert "  ATTESTED: 0 attested events" in text   # unchanged from the pre-slice render
    assert "q_attested" not in text                  # richer line only appears when n_total > 0
