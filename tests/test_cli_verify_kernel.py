import urllib.error

from polymer_claims.cli import main


def test_verify_kernel_smoke(capsys):
    rc = main(["verify-kernel"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "LICENSED @ REPRODUCED" in out
    assert "n_dmps=" in out
    assert "synthetic" in out.lower()       # honest labeling: not the real biology


def test_ingest_offline_error_is_friendly(tmp_path, capsys, monkeypatch):
    # Simulate GDC unreachable: make the fetch raise URLError.
    def _boom(*a, **k):
        raise urllib.error.URLError("network is unreachable")
    monkeypatch.setattr("polymer_claims.ingest.tcga_laml.fetch_file", _boom)
    rc = main(["ingest", "tcga-laml", "--data-dir", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "verify-kernel" in err          # points to the offline path
    assert "runbook" in err.lower()
    assert "Traceback" not in err          # no raw traceback
