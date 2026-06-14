from __future__ import annotations

import inspect

from polymer_protocol import run_cycle
from polymer_protocol.verify import verify_stage


def test_run_cycle_and_verify_stage_accept_replications():
    assert "replications" in inspect.signature(run_cycle).parameters
    assert "replications" in inspect.signature(verify_stage).parameters
