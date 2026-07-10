"""Task 1 — the claim-source registry: primary-literature citations for the probe claims."""
import dataclasses

import pytest

from polymer_claims.synbio.sources import SOURCES, ClaimSource


def test_sources_carry_ref():
    s = SOURCES["PLM-III"]
    assert isinstance(s, ClaimSource)
    assert s.ref  # non-empty citation
    # admissibility (the firewall tag) is populated in Phase 3; None is legal in Phase 1
    assert s.admissibility is None or isinstance(s.admissibility, str)


def test_sources_are_frozen():
    s = SOURCES["PLM-III"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.ref = "mutated"  # type: ignore[misc]


def test_five_probe_sources_present():
    # C1..C5 cite these; each must resolve to a source with a ref.
    for key in ("PLM-I", "PLM-II", "PLM-III", "PLM-VI", "PLM-XIII"):
        assert SOURCES[key].ref
