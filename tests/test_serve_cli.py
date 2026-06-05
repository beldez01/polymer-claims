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
