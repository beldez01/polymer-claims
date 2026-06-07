import types
import pytest

from polymer_claims import cli
from polymer_claims.cli import main
from polymer_claims.node import NodeRunner


def test_serve_help_registered():
    with pytest.raises(SystemExit) as e:
        main(["serve", "--help"])
    assert e.value.code == 0


def test_serve_missing_extra_prints_hint(monkeypatch, capsys):
    def boom():
        raise ImportError("no fastapi")
    monkeypatch.setattr(cli, "_import_server", boom)
    rc = main(["serve"])
    assert rc == 1
    assert "polymer-claims[serve]" in capsys.readouterr().err


def test_serve_builds_runner_and_runs(monkeypatch):
    seen = {}

    def fake_import():
        def run(app, host=None, port=None):
            seen["bind"] = (host, port)
        def create_app(runner, *, interval, origins):
            seen["runner"] = runner
            return "APP"
        return types.SimpleNamespace(run=run), create_app

    monkeypatch.setattr(cli, "_import_server", fake_import)
    rc = main(["serve", "--port", "1234"])
    assert rc == 0
    assert seen["bind"][1] == 1234
    assert isinstance(seen["runner"], NodeRunner)


def test_serve_refuses_non_loopback_without_flag(monkeypatch, capsys):
    # the guard must fire regardless of the serve extra; _import_server may be real or not
    rc = main(["serve", "--host", "0.0.0.0"])
    assert rc == 1
    assert "unsafe-remote-control" in capsys.readouterr().err


def test_serve_allows_non_loopback_with_flag(monkeypatch):
    seen = {}

    def fake_import():
        def run(app, host=None, port=None):
            seen["bind"] = (host, port)

        def create_app(runner, *, interval, origins):
            seen["runner"] = runner
            return "APP"

        import types as _t
        return _t.SimpleNamespace(run=run), create_app

    monkeypatch.setattr(cli, "_import_server", fake_import)
    rc = main(["serve", "--host", "0.0.0.0", "--unsafe-remote-control", "--port", "9099"])
    assert rc == 0
    assert seen["bind"] == ("0.0.0.0", 9099)


def test_serve_threads_max_frames(monkeypatch):
    seen = {}

    def fake_import():
        def run(app, host=None, port=None):
            pass

        def create_app(runner, *, interval, origins):
            seen["runner"] = runner
            return "APP"

        import types as _t
        return _t.SimpleNamespace(run=run), create_app

    monkeypatch.setattr(cli, "_import_server", fake_import)
    rc = main(["serve", "--max-frames", "42"])
    assert rc == 0
    assert seen["runner"].max_frames == 42


def test_serve_llm_threads_proposer_into_runner(monkeypatch):
    seen = {}
    def fake_import():
        def run(app, host=None, port=None): pass
        def create_app(runner, *, interval, origins): seen["runner"] = runner; return "APP"  # noqa: E702
        import types; return types.SimpleNamespace(run=run), create_app  # noqa: E702
    monkeypatch.setattr(cli, "_import_server", fake_import)
    import json
    from polymer_protocol import bridge_proposer
    from polymer_claims.llm_adapter import LLMGenerationAdapter
    dsl = {"proposals": [{"title": "g", "pattern_id": "adjusted_effect", "ontology_term": "g1",
                          "value": 0.01, "comparator": "lt", "threshold": 0.05}]}
    monkeypatch.setattr(cli, "_build_llm_proposer",
                        lambda model: bridge_proposer((LLMGenerationAdapter(lambda _p: json.dumps(dsl)),)))
    rc = main(["serve", "--llm", "--llm-every", "4"])
    assert rc == 0
    runner = seen["runner"]
    # the runner ticks; the LLM-generated claim eventually appears + licenses
    for _ in range(8):
        runner.tick()
    assert any(c.id.startswith("gen-llm-") and c.status.value == "licensed"
               for c in runner.corpus.claims)


def test_serve_llm_missing_key_errors(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_import_server",
        lambda: (__import__("types").SimpleNamespace(run=lambda *a, **k: None), lambda runner, **k: "APP"))
    monkeypatch.setattr(cli, "_build_llm_proposer",
        lambda model: (_ for _ in ()).throw(RuntimeError("set ANTHROPIC_API_KEY to use --llm")))
    rc = main(["serve", "--llm"])
    assert rc == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_default_seed_evolves():
    from polymer_claims.seed import default_seed_corpus
    corpus, kwargs = default_seed_corpus()
    assert "proposers" in kwargs
    r = NodeRunner.from_seed(corpus, **kwargs)
    for _ in range(10):
        r.tick()
    tl = r.snapshot()
    # the universe grows over time
    assert tl.frames[-1].stats.n_nodes >= tl.frames[0].stats.n_nodes
    # licensing spreads PROGRESSIVELY: run_cycle's budget=2.5 licenses a couple
    # per cycle rather than all at once — the gradual evolution the viewer shows.
    lic = [f.stats.n_licensed for f in tl.frames]
    assert all(b >= a for a, b in zip(lic, lic[1:]))          # non-decreasing
    assert max(b - a for a, b in zip(lic, lic[1:])) <= 3       # no big single-cycle jump
    assert lic[-1] >= 5                                        # reaches a healthy total
    # at least one representation-revision (octahedron) node appears by the end
    assert any(n.is_representation_revision for n in tl.frames[-1].topology.nodes)
