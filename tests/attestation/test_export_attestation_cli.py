from __future__ import annotations

import json

from polymer_claims.cli import main
from polymer_claims.io import dump_corpus
from tests.attestation._fixtures import corpus_with, licensed_claim, licensing, mc, sat


def _write_corpus(tmp_path):
    claim = licensed_claim("c1", licensing(sat(mc(dimnames_hash="sha256:" + "a" * 64))))
    path = tmp_path / "corpus.json"
    path.write_text(dump_corpus(corpus_with(claim)))
    return path


def test_export_attestation_writes_bundle(tmp_path):
    corpus_path = _write_corpus(tmp_path)
    out = tmp_path / "att.json"
    rc = main(["export-attestation", str(corpus_path), "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["bundleType"] == "https://polymerclaims.org/attestation-bundle/v1"
    assert data["attestations"][0]["subject"][0]["name"] == "c1"
