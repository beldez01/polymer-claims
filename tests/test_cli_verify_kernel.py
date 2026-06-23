from polymer_claims.cli import main


def test_verify_kernel_smoke(capsys):
    rc = main(["verify-kernel"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "LICENSED @ REPRODUCED" in out
    assert "n_dmps=" in out
    assert "synthetic" in out.lower()       # honest labeling: not the real biology
