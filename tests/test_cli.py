"""In-process smoke tests for the `polymer-claims` CLI."""
from __future__ import annotations

import json

from polymer_protocol import TopologyExport, TopologyTimeline

from polymer_claims.cli import main
from tests.conftest import licensing_corpus, make_claim


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------
def test_version(capsys):
    rc = main(["version"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "polymer-claims" in out
    assert "polymer-protocol" in out
    assert "polymer-grammar" in out


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
def test_validate_valid(tmp_path, capsys):
    claim = make_claim("a")
    path = tmp_path / "claim.json"
    path.write_text(claim.model_dump_json())
    rc = main(["validate", str(path)])
    assert rc == 0
    assert "valid" in capsys.readouterr().out


def test_validate_malformed(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text('{"id": "x", "not_a_real_field": 1}')
    rc = main(["validate", str(path)])
    assert rc == 1
    assert "invalid" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# run-cycle
# ---------------------------------------------------------------------------
def test_run_cycle_licenses(tmp_path, capsys):
    path = tmp_path / "corpus.json"
    path.write_text(licensing_corpus().model_dump_json())
    out = tmp_path / "out.json"
    rc = main(["run-cycle", str(path), "--out", str(out)])
    assert rc == 0
    assert "licensed=1" in capsys.readouterr().out
    assert out.exists()


# ---------------------------------------------------------------------------
# loop
# ---------------------------------------------------------------------------
def test_loop_runs_and_licenses(tmp_path, capsys):
    path = tmp_path / "corpus.json"
    path.write_text(licensing_corpus().model_dump_json())
    out = tmp_path / "out.json"
    rc = main(["loop", str(path), "--budget", "100", "--out", str(out)])
    captured = capsys.readouterr().out
    assert rc == 0
    # trace non-empty and at least one cycle ran
    assert "steps:" in captured
    assert "run_cycle" in captured
    assert "licensed=1" in captured
    assert out.exists()


# ---------------------------------------------------------------------------
# export-topology
# ---------------------------------------------------------------------------
def test_export_topology(tmp_path, capsys):
    path = tmp_path / "corpus.json"
    path.write_text(licensing_corpus().model_dump_json())
    out = tmp_path / "topo.json"
    rc = main(["export-topology", str(path), "--out", str(out)])
    assert rc == 0
    # round-trips back into a TopologyExport
    exp = TopologyExport.model_validate_json(out.read_text())
    assert isinstance(json.loads(out.read_text()), dict)
    assert exp is not None


# ---------------------------------------------------------------------------
# export-timeline
# ---------------------------------------------------------------------------
def test_export_timeline(tmp_path, capsys):
    path = tmp_path / "corpus.json"
    path.write_text(licensing_corpus().model_dump_json())
    out = tmp_path / "timeline.json"
    rc = main(["export-timeline", str(path), "--cycles", "3", "--out", str(out)])
    assert rc == 0
    tl = TopologyTimeline.model_validate_json(out.read_text())
    assert tl.n_cycles == 3
    assert len(tl.frames) == 4  # n_cycles + 1
    assert isinstance(json.loads(out.read_text()), dict)
