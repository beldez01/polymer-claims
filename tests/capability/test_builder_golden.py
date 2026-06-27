import json
from pathlib import Path
import pytest
from _variants import ALL_VARIANTS, canonical_form

GOLDEN = Path(__file__).parent / "golden"
CASES = [(g, name, b, kw) for g, vs in ALL_VARIANTS.items() for (name, b, kw) in vs]

@pytest.mark.parametrize("group,name,builder,kwargs", CASES, ids=[f"{g}/{n}" for g, n, _, _ in CASES])
def test_builder_matches_frozen_golden(group, name, builder, kwargs):
    fixture = GOLDEN / f"{group}__{name}.json"
    assert fixture.exists(), (
        f"missing frozen golden {fixture.name}; run scripts/capture_capability_goldens.py "
        f"BEFORE refactoring (never regenerate after)")
    assert canonical_form(builder(**kwargs)) == json.loads(fixture.read_text()), \
        f"{group}/{name} drifted from frozen golden"
