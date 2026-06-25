# tests/test_cli_verify_kernel_real.py
from polymer_claims.cli import _build_parser, main


def test_real_flags_parse():
    p = _build_parser()
    ns = p.parse_args(["verify-kernel", "--real", "--xena", "/tmp/m.gz",
                       "--cbioportal", "/tmp/cbio", "--cache-dir", "/tmp/cache", "--fetch"])
    assert ns.real and ns.xena == "/tmp/m.gz" and ns.cbioportal == "/tmp/cbio"
    assert ns.cache_dir == "/tmp/cache" and ns.fetch is True


def test_real_without_inputs_errors_actionably(tmp_path, capsys):
    rc = main(["verify-kernel", "--real", "--cache-dir", str(tmp_path / "empty")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "--fetch" in err or "not found" in err            # actionable PinnedInputError surfaced


def test_synthetic_path_unchanged(capsys):
    rc = main(["verify-kernel"])                              # no --real
    out = capsys.readouterr().out
    assert "synthetic" in out.lower()
    assert rc in (0, 1)
