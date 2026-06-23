import pytest
from polymer_claims.attested_ingest import (
    Resolution, parse_resolutions, validate_against_corpus,
)


def test_parse_minimal_row():
    text = '[{"subject_claim_id": "c1", "verdict": "failed", "attestation_ref": "doi:x"}]'
    rows = parse_resolutions(text)
    assert len(rows) == 1
    r = rows[0]
    assert r.subject_claim_id == "c1" and r.verdict == "failed"
    assert r.resolvability is None and r.license_epoch == 0


def test_parse_rejects_unknown_field():
    text = '[{"subject_claim_id": "c1", "verdict": "failed", "attestation_ref": "x", "bogus": 1}]'
    with pytest.raises(ValueError):
        parse_resolutions(text)


def test_parse_rejects_bad_verdict():
    text = '[{"subject_claim_id": "c1", "verdict": "maybe", "attestation_ref": "x"}]'
    with pytest.raises(ValueError):
        parse_resolutions(text)


def test_parse_rejects_negative_epoch():
    text = ('[{"subject_claim_id": "c1", "verdict": "failed", "attestation_ref": "x",'
            ' "license_epoch": -1}]')
    with pytest.raises(ValueError):
        parse_resolutions(text)
