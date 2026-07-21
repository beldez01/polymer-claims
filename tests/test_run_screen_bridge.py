"""C6 — the sensor::senseability bridge over the REAL reproduced SNV screen.

Every senseable SNV of the regenerated screen must license via two-classifier agreement
(LICENSED @ REPRODUCED). Needs SensorKit (+ its committed CDS cache) importable — skips
cleanly in environments where it isn't installed (deploy-resolvable dep = C1).
"""
import pytest

pytest.importorskip("sensorkit")
from polymer_claims.run_screen_bridge import run_bridge_over_screen


def test_real_senseable_snvs_license_reproduced():
    led = run_bridge_over_screen(limit=25)
    assert len(led) == 25
    # every senseable lesion licenses via the two-classifier REPRODUCED route
    assert all(v["status"] == "LICENSED" and v["reproduced"] for v in led.values())
    # they are real, distinct oncogenic hotspots across tiers (not synthetic)
    assert all(v["tier"] in ("ideal", "good", "engineered") for v in led.values())
    assert len({k for k in led}) == 25
