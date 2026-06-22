from __future__ import annotations

import base64
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


def _write_empty_corpus(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text(dump_corpus(corpus_with()))        # zero LICENSED claims
    return path

def test_export_attestation_dsse_ndjson(tmp_path, capsys):
    corpus_path = _write_corpus(tmp_path)
    assert main(["export-attestation", str(corpus_path), "--format", "dsse"]) == 0
    lines = [ln for ln in capsys.readouterr().out.split("\n") if ln]
    assert len(lines) == 1
    env = json.loads(lines[0])
    assert env["payloadType"] == "application/vnd.in-toto+json"
    assert env["signatures"] == []
    json.loads(base64.b64decode(env["payload"]))        # payload decodes to a Statement

def test_export_attestation_default_equals_format_bundle_bytes(tmp_path):
    corpus_path = _write_corpus(tmp_path)
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    assert main(["export-attestation", str(corpus_path), "--out", str(a)]) == 0
    assert main(["export-attestation", str(corpus_path), "--format", "bundle", "--out", str(b)]) == 0
    assert a.read_text() == b.read_text()               # default == explicit bundle, byte-for-byte

def test_export_attestation_dsse_stdout_equals_file(tmp_path, capsys):
    corpus_path = _write_corpus(tmp_path)
    out_file = tmp_path / "att.ndjson"
    assert main(["export-attestation", str(corpus_path), "--format", "dsse", "--out", str(out_file)]) == 0
    assert main(["export-attestation", str(corpus_path), "--format", "dsse"]) == 0
    assert out_file.read_text() == capsys.readouterr().out     # byte-identical, no print() divergence

def test_export_attestation_dsse_empty_emits_nothing(tmp_path, capsys):
    empty_path = _write_empty_corpus(tmp_path)
    assert main(["export-attestation", str(empty_path), "--format", "dsse"]) == 0
    assert capsys.readouterr().out == ""                # no blank line
