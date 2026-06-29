"""Tests for ExecutorDescriptor, ExecutorDescriptorRegistry,
ExecutorTrustEntry, ExecutorTrustRegistry."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from polymer_grammar import (
    ExecutorDescriptor,
    ExecutorDescriptorRegistry,
    ExecutorTrustEntry,
    ExecutorTrustRegistry,
)
from polymer_grammar.executor_credential import Component

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HASH_A = "sha256:" + "a" * 64
_HASH_B = "sha256:" + "b" * 64
_HASH_C = "sha256:" + "c" * 64
_HASH_D = "sha256:" + "d" * 64

_CANONICAL_ROLES = [
    "predictor",
    "baseline_predictor",
    "scorer",
    "evidence_transform",
]


def _make_components(**overrides) -> list[dict]:
    """Return the four canonical-order component dicts."""
    comps = [
        dict(role="predictor", identity="predictor-v1", implementation_hash=_HASH_A, config_hash=_HASH_B),
        dict(role="baseline_predictor", identity="baseline-v1", implementation_hash=_HASH_B, config_hash=_HASH_C),
        dict(role="scorer", identity="scorer-v1", implementation_hash=_HASH_C, config_hash=_HASH_D),
        dict(role="evidence_transform", identity="transform-v1", implementation_hash=_HASH_D, config_hash=_HASH_A),
    ]
    if overrides:
        comps = [dict(c, **overrides.get(c["role"], {})) for c in comps]
    return comps


def _make_descriptor(**overrides) -> ExecutorDescriptor:
    base: dict = dict(
        components=tuple(Component(**c) for c in _make_components()),
        version="1.0",
    )
    base.update(overrides)
    return ExecutorDescriptor(**base)


def _make_trust_entry(**overrides) -> ExecutorTrustEntry:
    base: dict = dict(
        descriptor_ref=_HASH_A,
        owner="org-x",
        trusted=True,
        version="1.0",
    )
    base.update(overrides)
    return ExecutorTrustEntry(**base)


# ---------------------------------------------------------------------------
# Component validators
# ---------------------------------------------------------------------------


def test_component_valid():
    c = Component(
        role="predictor",
        identity="pred-v1",
        implementation_hash=_HASH_A,
        config_hash=_HASH_B,
    )
    assert c.role == "predictor"


def test_component_empty_identity_raises():
    with pytest.raises(ValidationError):
        Component(role="predictor", identity="", implementation_hash=_HASH_A, config_hash=_HASH_B)


def test_component_non_sha256_implementation_hash_raises():
    with pytest.raises(ValidationError):
        Component(role="predictor", identity="pred-v1", implementation_hash="notsha256", config_hash=_HASH_B)


def test_component_non_sha256_config_hash_raises():
    with pytest.raises(ValidationError):
        Component(role="predictor", identity="pred-v1", implementation_hash=_HASH_A, config_hash="notsha256")


def test_component_uppercase_hex_in_hash_raises():
    with pytest.raises(ValidationError):
        Component(
            role="predictor",
            identity="pred-v1",
            implementation_hash="sha256:" + "A" * 64,
            config_hash=_HASH_B,
        )


def test_component_short_hex_in_hash_raises():
    with pytest.raises(ValidationError):
        Component(
            role="predictor",
            identity="pred-v1",
            implementation_hash="sha256:" + "a" * 63,
            config_hash=_HASH_B,
        )


# ---------------------------------------------------------------------------
# ExecutorDescriptor — valid
# ---------------------------------------------------------------------------


def test_valid_descriptor_constructs():
    d = _make_descriptor()
    assert d.version == "1.0"
    assert len(d.components) == 4


def test_content_hash_has_sha256_prefix():
    d = _make_descriptor()
    assert d.content_hash.startswith("sha256:")


def test_content_hash_is_64_hex_after_prefix():
    d = _make_descriptor()
    hex_part = d.content_hash[len("sha256:"):]
    assert len(hex_part) == 64
    assert all(ch in "0123456789abcdef" for ch in hex_part)


def test_content_hash_is_stable():
    d1 = _make_descriptor()
    d2 = _make_descriptor()
    assert d1.content_hash == d2.content_hash


def test_content_hash_changes_with_version():
    d1 = _make_descriptor(version="1.0")
    d2 = _make_descriptor(version="2.0")
    assert d1.content_hash != d2.content_hash


def test_content_hash_changes_with_component_identity():
    c_altered = [Component(**dict(_make_components()[0], identity="predictor-v2"))] + \
        [Component(**c) for c in _make_components()[1:]]
    d1 = _make_descriptor()
    d2 = _make_descriptor(components=tuple(c_altered))
    assert d1.content_hash != d2.content_hash


# ---------------------------------------------------------------------------
# ExecutorDescriptor — validators
# ---------------------------------------------------------------------------


def test_missing_baseline_predictor_role_raises():
    comps = [Component(**c) for c in _make_components() if c["role"] != "baseline_predictor"]
    with pytest.raises(ValidationError):
        ExecutorDescriptor(components=tuple(comps), version="1.0")


def test_missing_predictor_role_raises():
    comps = [Component(**c) for c in _make_components() if c["role"] != "predictor"]
    with pytest.raises(ValidationError):
        ExecutorDescriptor(components=tuple(comps), version="1.0")


def test_missing_scorer_role_raises():
    comps = [Component(**c) for c in _make_components() if c["role"] != "scorer"]
    with pytest.raises(ValidationError):
        ExecutorDescriptor(components=tuple(comps), version="1.0")


def test_missing_evidence_transform_role_raises():
    comps = [Component(**c) for c in _make_components() if c["role"] != "evidence_transform"]
    with pytest.raises(ValidationError):
        ExecutorDescriptor(components=tuple(comps), version="1.0")


def test_duplicate_role_raises():
    """Two 'predictor' components and no baseline_predictor."""
    raw = _make_components()
    # Replace baseline_predictor with another predictor
    raw[1] = dict(role="predictor", identity="predictor-v2", implementation_hash=_HASH_C, config_hash=_HASH_D)
    comps = [Component(**c) for c in raw]
    with pytest.raises(ValidationError):
        ExecutorDescriptor(components=tuple(comps), version="1.0")


def test_wrong_role_order_raises():
    """Swap predictor and baseline_predictor — canonical order violated."""
    raw = _make_components()
    raw[0], raw[1] = raw[1], raw[0]  # swap order
    comps = [Component(**c) for c in raw]
    with pytest.raises(ValidationError):
        ExecutorDescriptor(components=tuple(comps), version="1.0")


def test_duplicate_identity_raises():
    raw = _make_components()
    raw[1] = dict(raw[1], identity="predictor-v1")  # same as raw[0]
    comps = [Component(**c) for c in raw]
    with pytest.raises(ValidationError):
        ExecutorDescriptor(components=tuple(comps), version="1.0")


# ---------------------------------------------------------------------------
# ExecutorDescriptorRegistry
# ---------------------------------------------------------------------------


def test_empty_descriptor_registry_is_valid():
    reg = ExecutorDescriptorRegistry()
    assert reg.descriptors == ()


def test_descriptor_registry_resolve_round_trip():
    d = _make_descriptor()
    reg = ExecutorDescriptorRegistry(descriptors=(d,))
    assert reg.resolve(d.content_hash) == d


def test_descriptor_registry_resolve_unknown_returns_none():
    d = _make_descriptor()
    reg = ExecutorDescriptorRegistry(descriptors=(d,))
    assert reg.resolve("sha256:" + "0" * 64) is None


def test_descriptor_registry_duplicate_content_hash_raises():
    d1 = _make_descriptor()
    d2 = _make_descriptor()  # identical → same content_hash
    assert d1.content_hash == d2.content_hash
    with pytest.raises(ValidationError):
        ExecutorDescriptorRegistry(descriptors=(d1, d2))


def test_descriptor_registry_distinct_descriptors_ok():
    d1 = _make_descriptor(version="1.0")
    d2 = _make_descriptor(version="2.0")
    assert d1.content_hash != d2.content_hash
    reg = ExecutorDescriptorRegistry(descriptors=(d1, d2))
    assert reg.resolve(d1.content_hash) == d1
    assert reg.resolve(d2.content_hash) == d2


# ---------------------------------------------------------------------------
# ExecutorTrustEntry
# ---------------------------------------------------------------------------


def test_trust_entry_valid():
    e = _make_trust_entry()
    assert e.trusted is True
    assert e.owner == "org-x"


def test_trust_entry_non_sha256_descriptor_ref_raises():
    with pytest.raises(ValidationError):
        _make_trust_entry(descriptor_ref="not-a-sha256-ref")


def test_trust_entry_empty_owner_raises():
    with pytest.raises(ValidationError):
        _make_trust_entry(owner="")


def test_trust_entry_blank_owner_raises():
    with pytest.raises(ValidationError):
        _make_trust_entry(owner="   ")


def test_trust_entry_trusted_false_is_valid():
    e = _make_trust_entry(trusted=False)
    assert e.trusted is False


# ---------------------------------------------------------------------------
# ExecutorTrustRegistry
# ---------------------------------------------------------------------------


def test_empty_trust_registry_is_valid():
    reg = ExecutorTrustRegistry()
    assert reg.entries == ()


def test_trust_registry_resolve_round_trip():
    e = _make_trust_entry(descriptor_ref=_HASH_A)
    reg = ExecutorTrustRegistry(entries=(e,))
    assert reg.resolve(_HASH_A) == e


def test_trust_registry_resolve_unknown_returns_none():
    e = _make_trust_entry(descriptor_ref=_HASH_A)
    reg = ExecutorTrustRegistry(entries=(e,))
    assert reg.resolve(_HASH_B) is None


def test_trust_registry_duplicate_descriptor_ref_raises():
    e1 = _make_trust_entry(descriptor_ref=_HASH_A, owner="org-x")
    e2 = _make_trust_entry(descriptor_ref=_HASH_A, owner="org-y")
    with pytest.raises(ValidationError):
        ExecutorTrustRegistry(entries=(e1, e2))


def test_trust_registry_distinct_refs_ok():
    e1 = _make_trust_entry(descriptor_ref=_HASH_A, owner="org-x")
    e2 = _make_trust_entry(descriptor_ref=_HASH_B, owner="org-y")
    reg = ExecutorTrustRegistry(entries=(e1, e2))
    assert reg.resolve(_HASH_A) == e1
    assert reg.resolve(_HASH_B) == e2


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


def test_descriptor_is_frozen():
    d = _make_descriptor()
    with pytest.raises(Exception):
        d.version = "9.9"  # type: ignore[misc]


def test_trust_entry_is_frozen():
    e = _make_trust_entry()
    with pytest.raises(Exception):
        e.owner = "hacked"  # type: ignore[misc]
