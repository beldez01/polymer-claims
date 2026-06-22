"""Tests for render_certificate_text — no-laundering invariant."""
from polymer_protocol.calibration import (
    CalibrationLedger,
    ResolutionRecord,
    ResolutionKind,
    CalibrationTarget,
    ResolutionVerdict,
    PressureKind,
)
from polymer_claims.attestation import build_certificate, render_certificate_text

# Reuse the same licensed_corpus() defined in test_certificate.py to avoid duplication.
from tests.test_certificate import licensed_corpus


def _ledger():
    defn = [
        ResolutionRecord(
            subject_claim_id=f"d{i}",
            license_epoch=0,
            resolution_kind=ResolutionKind.DEFINITIONAL,
            calibration_target=CalibrationTarget.REALIZED_FDR,
            verdict=(ResolutionVerdict.FAILED if i == 0 else ResolutionVerdict.UPHELD),
            stated_q=0.05,
            observed_at_cycle=0,
            constructed_truth=(i != 0),
            model_id="m",
            batch_id="b",
        )
        for i in range(10)
    ]
    anch = [
        ResolutionRecord(
            subject_claim_id="a1",
            license_epoch=0,
            resolution_kind=ResolutionKind.ANCHORED,
            calibration_target=CalibrationTarget.WARRANT_SURVIVAL,
            verdict=ResolutionVerdict.FAILED,
            stated_q=0.05,
            observed_at_cycle=3,
            pressure_kind=PressureKind.DEFEAT,
        )
    ]
    return CalibrationLedger(records=tuple(defn + anch))


def test_render_has_headline_fdr_and_separates_field_calibration():
    corpus = licensed_corpus()
    cid = next(c.id for c in corpus.claims if c.status.value == "licensed")
    text = render_certificate_text(build_certificate(corpus, cid, ledger=_ledger(), target_q=0.05))
    assert "realized FDR" in text
    assert "Warrant stability" in text  # field-calibration heading present
    # The no-laundering invariant: the field-calibration heading must appear AFTER
    # the headline q line — anchored warrant-failure rate is never the headline q.
    headline_idx = text.index("Corpus target q")
    field_idx = text.index("Warrant stability")
    assert field_idx > headline_idx, (
        f"Warrant stability block (pos {field_idx}) must appear after headline q "
        f"(pos {headline_idx}) — no-laundering invariant violated"
    )


def test_render_standing_only_when_no_ledger():
    """ledger=None produces a standing-only render: no calibration block, no 'Corpus target q'."""
    corpus = licensed_corpus()
    cid = next(c.id for c in corpus.claims if c.status.value == "licensed")
    cert = build_certificate(corpus, cid, target_q=0.05)  # no ledger
    text = render_certificate_text(cert)
    assert "standing-only" in text
    assert "Corpus target q" not in text
    assert "Warrant stability" not in text
    # Interpretation line is still present
    assert cert.interpretation in text
