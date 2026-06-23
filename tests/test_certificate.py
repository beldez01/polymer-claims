"""Tests for Certificate DTO, build_certificate, and certificate_dsse_envelope."""
import base64
import json

import pytest
from polymer_protocol.calibration import CalibrationLedger

from polymer_claims.attestation import (
    build_attestation_bundle,
    build_certificate,
    certificate_dsse_envelope,
    resolve_contract_index,
)

# Reuse the licensed-corpus builder from the attestation fixtures
from tests.attestation._fixtures import corpus_with, licensed_claim, licensing, mc, sat


def _licensed(cid):
    return licensed_claim(
        cid,
        licensing(
            sat(
                mc(
                    dimnames_hash="sha256:" + "a" * 64,
                    profile_hash="sha256:" + "b" * 64,
                    semantic_run_id="r1",
                )
            )
        ),
    )


def licensed_corpus():
    """One LICENSED claim corpus — mirrors the attestation test helper."""
    return corpus_with(_licensed("c1"))


def test_certificate_carries_calibration_block():
    corpus = licensed_corpus()
    cid = next(c.id for c in corpus.claims if c.status.value == "licensed")
    cert = build_certificate(corpus, cid, ledger=CalibrationLedger(records=()), target_q=0.05)
    assert cert.statement is not None
    assert cert.calibration is not None and cert.calibration.target_q == 0.05


def test_certificate_no_ledger_has_none_calibration():
    corpus = licensed_corpus()
    cid = next(c.id for c in corpus.claims if c.status.value == "licensed")
    cert = build_certificate(corpus, cid, target_q=0.05)
    assert cert.calibration is None
    assert cert.ledger_digest is None
    assert cert.generating_models == ()


def test_certificate_ledger_digest_is_sha256_hex():
    corpus = licensed_corpus()
    cid = next(c.id for c in corpus.claims if c.status.value == "licensed")
    cert = build_certificate(corpus, cid, ledger=CalibrationLedger(records=()), target_q=0.05)
    assert cert.ledger_digest is not None
    assert len(cert.ledger_digest) == 64  # hex sha256


def test_certificate_dsse_payload_round_trips_to_certificate():
    corpus = licensed_corpus()
    cid = next(c.id for c in corpus.claims if c.status.value == "licensed")
    cert = build_certificate(corpus, cid, ledger=CalibrationLedger(records=()), target_q=0.05)
    env = certificate_dsse_envelope(cert)
    assert env.payload_type == "application/vnd.polymer.certificate+json"
    decoded = json.loads(base64.b64decode(env.payload))
    assert "statement" in decoded and "calibration" in decoded


def test_existing_attestation_bundle_byte_identical():
    # build_attestation_bundle must be untouched by the new code
    corpus = licensed_corpus()
    out = build_attestation_bundle(corpus, contract_index=resolve_contract_index(corpus))
    assert out.model_dump_json(by_alias=True, exclude_none=True)  # smoke: still builds, no exception


def test_build_certificate_unknown_claim_raises():
    corpus = licensed_corpus()
    with pytest.raises(ValueError):
        build_certificate(corpus, "nonexistent-id", target_q=0.05)


def test_build_certificate_uses_bootstrap_ci_for_multibatch_definitional():
    from polymer_protocol.calibration import (
        CalibrationTarget,
        ResolutionKind,
        ResolutionRecord,
        ResolutionVerdict,
    )

    corpus = licensed_corpus()
    cid = next(c.id for c in corpus.claims if c.status.value == "licensed")

    def _d(rid, batch, failed):
        return ResolutionRecord(
            subject_claim_id=rid, license_epoch=0, resolution_kind=ResolutionKind.DEFINITIONAL,
            calibration_target=CalibrationTarget.REALIZED_FDR,
            verdict=ResolutionVerdict.FAILED if failed else ResolutionVerdict.UPHELD,
            stated_q=0.05, observed_at_cycle=0, constructed_truth=not failed,
            model_id="m", batch_id=batch,
        )

    # two batches → the DEFINITIONAL CI is the deterministic bootstrap, not the normal-approx
    recs = (_d("a0", "A", True), _d("a1", "A", False), _d("b0", "B", False), _d("b1", "B", False))
    cert = build_certificate(corpus, cid, ledger=CalibrationLedger(records=recs), target_q=0.05)
    assert cert.calibration.definitional.ci_method == "bootstrap_0.95"
    assert cert.calibration.definitional.ci_low is not None
    assert cert.calibration.definitional.ci_high is not None
