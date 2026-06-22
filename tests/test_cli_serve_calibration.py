"""Slice 1: `serve --calibration` forwards the calibration ledger path into NodeRunner.

The live node (`serve`) is the only CLI path that drives `NodeRunner.tick()`, where the
calibration hook fires. These tests assert the forwarding without starting a real server
(uvicorn + create_app are stubbed; NodeRunner.from_seed is captured). The hook's actual
record-writing is covered by tests/test_calibration_store.py.
"""
import polymer_claims.cli as cli


def _serve_capturing(monkeypatch, argv):
    """Run `serve …` in-process, stubbing the server, and capture from_seed kwargs."""
    captured: dict = {}

    def fake_from_seed(corpus, **kw):
        captured.update(kw)
        return object()  # a dummy runner; the server is stubbed so nothing uses it

    monkeypatch.setattr(cli.NodeRunner, "from_seed", fake_from_seed)

    class _FakeUvicorn:
        @staticmethod
        def run(app, **kw):  # never actually serve
            return None

    monkeypatch.setattr(cli, "_import_server", lambda: (_FakeUvicorn, lambda runner, **kw: object()))

    args = cli._build_parser().parse_args(argv)
    rc = args.func(args)
    return rc, captured


def test_serve_forwards_calibration_path(monkeypatch, tmp_path):
    cal = tmp_path / "cal.jsonl"
    rc, captured = _serve_capturing(monkeypatch, ["serve", "--calibration", str(cal)])
    assert rc == 0
    assert captured.get("calibration_path") == str(cal)


def test_serve_forwards_calibration_epoch(monkeypatch, tmp_path):
    cal = tmp_path / "cal.jsonl"
    ep = tmp_path / "ep.json"
    rc, captured = _serve_capturing(
        monkeypatch, ["serve", "--calibration", str(cal), "--calibration-epoch", str(ep)]
    )
    assert rc == 0
    assert captured.get("calibration_path") == str(cal)
    assert captured.get("calibration_epoch_path") == str(ep)


def test_serve_without_flag_passes_no_calibration(monkeypatch):
    # default branch (no flags) → byte-identical: no calibration kwargs forwarded
    rc, captured = _serve_capturing(monkeypatch, ["serve"])
    assert rc == 0
    assert "calibration_path" not in captured
    assert "calibration_epoch_path" not in captured
