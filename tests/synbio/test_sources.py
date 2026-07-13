"""Task 1 — the claim-source registry: primary-literature citations for the probe claims."""
import dataclasses
from pathlib import Path

import pytest

from polymer_claims.synbio.sources import SOURCES, ClaimSource

_REPO = Path(__file__).resolve().parents[2]


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


def test_sources_resolve_in_repo():
    # every ref points at a file that exists inside the repo (no sibling taps)
    for key, src in SOURCES.items():
        p = _REPO / src.ref
        assert p.exists(), f"{key}: {src.ref} not found in-repo"


def test_in_scope_chapters_present():
    for key in ("PLM-II", "PLM-III", "PLM-VI", "PLM-VII", "PLM-VIII", "PLM-XIII"):
        assert key in SOURCES
