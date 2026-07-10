"""Task 8: CLI smoke test — `pharmaco-populate` is registered and listed in --help. Does NOT
exercise the real pipeline (that's test_real_controls_slow.py); keeps core CI fast and
extra-free (core `import polymer_claims.cli` must stay clean without `[pharmaco]`)."""
from __future__ import annotations

import subprocess
import sys


def test_pharmaco_populate_in_help():
    out = subprocess.run(
        [sys.executable, "-m", "polymer_claims.cli", "--help"],
        capture_output=True, text=True,
    )
    assert "pharmaco-populate" in out.stdout


def test_core_cli_import_stays_clean_without_pharmaco_extra():
    """Importing the CLI module must not require pandas/numpy/scipy (the [pharmaco] extra)."""
    out = subprocess.run(
        [sys.executable, "-c", "import polymer_claims.cli"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
