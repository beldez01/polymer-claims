"""Real-data kernel parity gate. This module's run_real_kernel_proof (Task 4) resolves the three
pinned inputs, rebuilds se:tcga_laml_idh@2 into a temp contract root, asserts content-address parity
vs the committed pins, runs the REAL n-DMP gate, and requires LICENSED @ REPRODUCED. It proves the
pinned real-data computation reproduces — NOT data veracity (spec §0)."""
from __future__ import annotations

import json
from importlib.resources import files


def load_pins() -> dict:
    """Load the committed reference pins (real_kernel_pins.json), via importlib.resources so an
    installed package resolves it cleanly."""
    return json.loads(
        files("polymer_claims.ingest").joinpath("real_kernel_pins.json").read_text())
