import json
from polymer_claims.cli import main
from tests.attestation._fixtures import licensed_claim, licensing, corpus_with, mc, sat


def _write_corpus(tmp_path):
    corpus = corpus_with(licensed_claim("c1", licensing(sat(mc()))))
    p = tmp_path / "corpus.json"
    p.write_text(corpus.model_dump_json())
    return p


def test_ingest_attested_smoke(tmp_path, capsys):
    corpus_path = _write_corpus(tmp_path)
    res_path = tmp_path / "res.json"
    res_path.write_text(json.dumps([
        {"subject_claim_id": "c1", "verdict": "failed", "attestation_ref": "doi:10.1056/x"}
    ]))
    ledger = tmp_path / "calib.jsonl"
    out = tmp_path / "out.json"
    rc = main(["ingest-attested", "--corpus", str(corpus_path),
               "--resolutions", str(res_path), "--calibration", str(ledger),
               "--out", str(out)])
    assert rc == 0
    assert ledger.exists() and out.exists()
    data = json.loads(out.read_text())
    assert any(c["id"].startswith("attest-") for c in data["claims"])


def test_ingest_attested_unknown_subject_errors(tmp_path, capsys):
    corpus_path = _write_corpus(tmp_path)
    res_path = tmp_path / "res.json"
    res_path.write_text(json.dumps([
        {"subject_claim_id": "nope", "verdict": "failed", "attestation_ref": "x"}
    ]))
    rc = main(["ingest-attested", "--corpus", str(corpus_path),
               "--resolutions", str(res_path), "--calibration", str(tmp_path / "c.jsonl")])
    assert rc == 1
    assert "nope" in capsys.readouterr().err
