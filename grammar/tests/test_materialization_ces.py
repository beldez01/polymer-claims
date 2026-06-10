"""CES-0: MaterializationContext gains three additive-optional content-address keys."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from polymer_grammar import MaterializationContext


def test_back_compat_three_arg_construction_unchanged():
    # Existing call sites pass only id/api_version/data_version — must still work,
    # and the new fields default to None.
    ctx = MaterializationContext(id="M1", api_version="v1", data_version="d1")
    assert ctx.semantic_run_id is None
    assert ctx.profile_hash is None
    assert ctx.dimnames_hash is None


def test_new_fields_round_trip():
    ctx = MaterializationContext(
        id="M1",
        api_version="v1",
        data_version="d1",
        semantic_run_id="sha256:run",
        profile_hash="sha256:prof",
        dimnames_hash="sha256:dims",
    )
    assert ctx.semantic_run_id == "sha256:run"
    assert ctx.profile_hash == "sha256:prof"
    assert ctx.dimnames_hash == "sha256:dims"
    # frozen + extra-forbid still hold
    with pytest.raises(ValidationError):
        MaterializationContext(id="M1", api_version="v1", data_version="d1", bogus="x")
