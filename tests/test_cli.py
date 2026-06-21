"""In-process smoke tests for the `polymer-claims` CLI."""
from __future__ import annotations

import json

import pytest
from polymer_protocol import Corpus, TopologyExport, TopologyTimeline

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
    assert "licensed=1" in capsys.readouterr().err
    assert out.exists()


def test_run_cycle_stdout_is_clean_json(capsys, tmp_path):
    p = tmp_path / "c.json"
    p.write_text(licensing_corpus().model_dump_json())
    rc = main(["run-cycle", str(p)])
    out = capsys.readouterr()
    assert rc == 0
    Corpus.model_validate_json(out.out)          # stdout parses as a Corpus
    assert "status:" in out.err                  # the human summary went to stderr


def test_run_cycle_llm_missing_key_or_extra(monkeypatch, capsys, tmp_path):
    # force the helper to raise (simulates missing extra/key) -> hint on stderr, nonzero exit
    from polymer_claims import cli
    monkeypatch.setattr(cli, "_build_llm_proposer", lambda model: (_ for _ in ()).throw(RuntimeError("set ANTHROPIC_API_KEY to use --llm")))
    p = tmp_path / "c.json"
    p.write_text(licensing_corpus().model_dump_json())
    rc = main(["run-cycle", str(p), "--llm"])
    assert rc == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_run_cycle_llm_wires_generator(monkeypatch, capsys, tmp_path):
    # inject a fake proposer (stub LLM adapter via bridge) so a gen-llm-* claim appears; no network
    import json
    from polymer_protocol import bridge_proposer
    from polymer_claims import cli
    from polymer_claims.llm_adapter import LLMGenerationAdapter
    dsl = {"proposals": [{"title": "g", "pattern_id": "adjusted_effect", "ontology_term": "g1",
                          "value": 0.01, "comparator": "lt", "threshold": 0.05}]}
    monkeypatch.setattr(cli, "_build_llm_proposer",
                        lambda model: bridge_proposer((LLMGenerationAdapter(lambda _p: json.dumps(dsl)),)))
    p = tmp_path / "c.json"
    p.write_text(licensing_corpus().model_dump_json())
    out = tmp_path / "out.json"
    rc = main(["run-cycle", str(p), "--llm", "--out", str(out)])
    assert rc == 0
    from polymer_protocol import Corpus
    result = Corpus.model_validate_json(out.read_text())
    assert any(c.id.startswith("gen-llm-") for c in result.claims)


# ---------------------------------------------------------------------------
# loop
# ---------------------------------------------------------------------------
def test_loop_runs_and_licenses(tmp_path, capsys):
    path = tmp_path / "corpus.json"
    path.write_text(licensing_corpus().model_dump_json())
    out = tmp_path / "out.json"
    rc = main(["loop", str(path), "--budget", "100", "--out", str(out)])
    captured = capsys.readouterr().err
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


def test_export_timeline_stdout_is_clean_json(capsys, tmp_path):
    p = tmp_path / "c.json"
    p.write_text(licensing_corpus().model_dump_json())
    rc = main(["export-timeline", str(p), "--cycles", "2"])
    out = capsys.readouterr()
    assert rc == 0
    TopologyTimeline.model_validate_json(out.out)
    assert "frames:" in out.err


# ---------------------------------------------------------------------------
# export-consistency
# ---------------------------------------------------------------------------
def test_export_consistency_emits_report(tmp_path, capsys):
    pytest.importorskip("numpy")
    path = tmp_path / "corpus.json"
    path.write_text(licensing_corpus().model_dump_json())
    rc = main(["export-consistency", str(path)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "inconsistency_energy" in out and "h0_dim" in out
